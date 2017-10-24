# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _name = 'pos.config'
    _description = u'POS设置'

    @api.model
    def _default_warehouse(self):
        return self._default_warehouse_impl()

    @api.model
    def _default_warehouse_impl(self):
        if self.env.context.get('warehouse_type'):
            return self.env['warehouse'].get_warehouse_by_type(
                self.env.context.get('warehouse_type'))

    name = fields.Char(string=u'POS名称', index=True, required=True)
    cash_control = fields.Boolean(string=u'现金管理')
    receipt_footer = fields.Text(
        string=u'收据页脚', help=u"在打印出来的收据中插入一段简短文字作为页脚。")
    proxy_ip = fields.Char(string=u'IP地址', size=45,
                           help=u'硬件代理的主机名或IP地址，如果留空则会被自动检测到。')
    active = fields.Boolean(u'有效', default=True)
    uuid = fields.Char(u'唯一识别码', readonly=True,
                       default=lambda self: str(uuid.uuid4()), help=u'唯一识别码')
    sequence_id = fields.Many2one(
        'ir.sequence', string=u'订单号序列', readonly=True, copy=False)
    session_ids = fields.One2many('pos.session', 'config_id', string=u'会话')
    current_session_id = fields.Many2one(
        'pos.session', compute='_compute_current_session', string=u"当前会话")
    current_session_state = fields.Char(compute='_compute_current_session')
    last_session_closing_date = fields.Date(
        u'最近会话关闭日期', compute='_compute_last_session')

    company_id = fields.Many2one(
        'res.company', string=u'公司', required=True, default=lambda self: self.env.user.company_id)
    group_pos_manager_id = fields.Many2one('res.groups', string=u'POS管理组',
                                           help=u'管理POS这个POS缓存的组')
    group_pos_user_id = fields.Many2one('res.groups', string=u'POS用户组',
                                        help=u'可以使用这POS页面的人')
    tip_product_id = fields.Many2one('goods', string=u'提示产品')
    bank_account_ids = fields.Many2many(
        'bank.account', 'pos_config_bank_account_rel',
        'pos_config_id', 'bank_account_id',
        u'可用的结算账户',
    )
    warehouse_id = fields.Many2one('warehouse',
                                   u'调出仓库',
                                   required=True,
                                   ondelete='restrict',
                                   default=_default_warehouse,
                                   help=u'商品将从该仓库调出')

    @api.depends('session_ids')
    def _compute_current_session(self):
        for pos_config in self:
            session = pos_config.session_ids.filtered(
                lambda r: r.user_id.id == self.env.uid and not r.state == 'closed')
            pos_config.current_session_id = session
            pos_config.current_session_state = session.state

    @api.depends('session_ids')
    def _compute_last_session(self):
        PosSession = self.env['pos.session']
        for pos_config in self:
            session = PosSession.search_read(
                [('config_id', '=', pos_config.id), ('state', '=', 'closed')],
                ['stop_at'],
                order="stop_at desc", limit=1)
            if session:
                pos_config.last_session_closing_date = session[0]['stop_at']
            else:
                pos_config.last_session_closing_date = False

    @api.multi
    def name_get(self):
        result = []
        for config in self:
            if (not config.session_ids) or (config.session_ids[0].state == 'closed'):
                result.append((config.id, config.name +
                               ' (' + _('not used') + ')'))
                continue
            result.append((config.id, config.name +
                           ' (' + config.session_ids[0].user_id.name + ')'))
        return result

    @api.model
    def create(self, values):
        IrSequence = self.env['ir.sequence'].sudo()
        val = {
            'name': _('POS Order %s') % values['name'],
            'padding': 4,
            'prefix': "%s/" % values['name'],
            'code': "pos.order",
            'company_id': values.get('company_id', False),
        }
        values['sequence_id'] = IrSequence.create(val).id
        # TODO master: add field sequence_line_id on model
        IrSequence.create(val)
        return super(PosConfig, self).create(values)

    @api.multi
    def unlink(self):
        for pos_config in self.filtered(lambda pos_config: pos_config.sequence_id):
            pos_config.sequence_id.unlink()
        return super(PosConfig, self).unlink()

    # Methods to open the POS
    @api.multi
    def open_ui(self):
        assert len(self.ids) == 1, "只能同时打开一个缓存"
        return {
            'type': 'ir.actions.act_url',
            'url':   '/pos/web/',
            'target': 'self',
        }

    @api.multi
    def open_existing_session_cb_close(self):
        assert len(self.ids) == 1, "只能同时打开一个缓存"
        if self.current_session_id.cash_control:
            self.current_session_id.action_pos_session_closing_control()
        return self.open_session_cb()

    @api.multi
    def open_session_cb(self):
        """打开一个新会话"""
        assert len(self.ids) == 1, "只能同时打开一个缓存"
        if not self.current_session_id:
            self.current_session_id = self.env['pos.session'].create({
                'user_id': self.env.uid,
                'config_id': self.id
            })
            if self.current_session_id.state == 'opened':
                return self.open_ui()
            return self._open_session(self.current_session_id.id)
        return self._open_session(self.current_session_id.id)

    @api.multi
    def open_existing_session_cb(self):
        """打开一个会话"""
        assert len(self.ids) == 1, "只能同时打开一个缓存"
        return self._open_session(self.current_session_id.id)

    def _open_session(self, session_id):
        return {
            'name': _('Session'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'pos.session',
            'res_id': session_id,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
