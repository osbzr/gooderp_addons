# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PosConfig(models.Model):
    _name = 'pos.config'
    _description = u'POS设置'

    name = fields.Char(string='Point of Sale Name', index=True, required=True)
    cash_control = fields.Boolean(string='Cash Control')
    receipt_footer = fields.Text(string='Receipt Footer', help="A short text that will be inserted as a footer in the printed receipt")
    proxy_ip = fields.Char(string='IP Address', size=45,
        help='The hostname or ip address of the hardware proxy, Will be autodetected if left empty')
    active = fields.Boolean(default=True)
    uuid = fields.Char(readonly=True, default=lambda self: str(uuid.uuid4()), help='唯一识别码')
    sequence_id = fields.Many2one('ir.sequence', string='Order IDs Sequence', readonly=True, copy=False)
    session_ids = fields.One2many('pos.session', 'config_id', string='Sessions')
    last_session_closing_date = fields.Date()

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    group_pos_manager_id = fields.Many2one('res.groups', string='Point of Sale Manager Group',
        help='管理POS这个POS缓存的组')
    group_pos_user_id = fields.Many2one('res.groups', string='Point of Sale User Group',
        help='可以使用这POS页面的人')
    tip_product_id = fields.Many2one('goods', string='Tip Product' )

    @api.multi
    def name_get(self):
        result = []
        for config in self:
            if (not config.session_ids) or (config.session_ids[0].state == 'closed'):
                result.append((config.id, config.name + ' (' + _('not used') + ')'))
                continue
            result.append((config.id, config.name + ' (' + config.session_ids[0].user_id.name + ')'))
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
