# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class SellToBuyWizard(models.TransientModel):
    _name = 'sell.to.buy.wizard'
    _description = u'根据销货订单生成购货订单向导'

    sell_line_ids = fields.Many2many(
        'sell.order.line',
        string=u'销货单行',
        default=lambda self: [(4, s.id, s.goods_id.name, s.order_id.name) for s in self.env['sell.order.line'].search(
            [('is_bought', '=', False)], order='order_id')],
        help=u'对应的销货订单行')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def button_ok(self):
        pass
