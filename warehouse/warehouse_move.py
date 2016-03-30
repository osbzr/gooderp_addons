# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp import models, fields, api


class wh_move(models.Model):
    _name = 'wh.move'

    MOVE_STATE = [
        ('draft', u'草稿'),
        ('done', u'已审核'),
    ]

    origin = fields.Char(u'源单类型', required=True)
    name = fields.Char(u'单据编号', copy=False, default='/')
    state = fields.Selection(MOVE_STATE, u'状态', copy=False, default='draft')
    partner_id = fields.Many2one('partner', u'业务伙伴')
    date = fields.Date(u'单据日期', copy=False, default=fields.Date.context_today)
    approve_uid = fields.Many2one('res.users', u'审核人', copy=False)
    approve_date = fields.Datetime(u'审核日期', copy=False)
    line_out_ids = fields.One2many('wh.move.line', 'move_id', u'明细', domain=[('type', '=', 'out')], context={'type': 'out'}, copy=True)
    line_in_ids = fields.One2many('wh.move.line', 'move_id', u'明细', domain=[('type', '=', 'in')], context={'type': 'in'}, copy=True)
    note = fields.Text(u'备注')

    @api.multi
    def unlink(self):
        for move in self:
            if move.state == 'done':
                raise osv.except_osv(u'错误', u'不可以删除已经完成的单据')

        return super(wh_move, self).unlink()

    def prev_approve_order(self):
        for order in self:
            if not order.line_out_ids and not order.line_in_ids:
                raise osv.except_osv(u'错误', u'单据的明细行不可以为空')

    @api.multi
    def approve_order(self):
        for order in self:
            order.prev_approve_order()
            order.line_out_ids.action_done()
            order.line_in_ids.action_done()

        return self.write({
                'approve_uid': self.env.uid,
                'approve_date': fields.Datetime.now(self),
                'state': 'done',
            })

    def prev_cancel_approved_order(self):
        pass

    @api.multi
    def cancel_approved_order(self):
        for order in self:
            order.prev_cancel_approved_order()
            order.line_out_ids.action_cancel()
            order.line_in_ids.action_cancel()

        return self.write({
                'approve_uid': False,
                'approve_date': False,
                'state': 'draft',
            })
