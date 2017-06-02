# -*- coding: utf-8 -*-

from odoo import fields, models, api


class cost_line(models.Model):
    _inherit = 'cost.line'

    sell_id = fields.Many2one('sell.delivery', u'出库单号',
                              ondelete='cascade',
                              help=u'与销售费用相关联的出库单号')

class money_order(models.Model):
    _inherit = 'money.order'

    sell_id = fields.Many2one('sell.order', u'销售订单',
                              ondelete='restrict',
                              help=u'与付款相关的销售订单号')

    @api.multi
    def money_order_done(self):
        return_vals = super(money_order, self).money_order_done()
        for order_row in self:
            if order_row.type == 'get' and order_row.sell_id:
                order_row.sell_id.received_amount =\
                 sum([order.amount for order in self.search([('sell_id', '=',
                                                              order_row.sell_id.id),
                                                             ('state', '=', 'done')])])
        return return_vals


    @api.multi
    def money_order_draft(self):
        return_vals = super(money_order, self).money_order_draft()
        for order_row in self:
            if order_row.type == 'get' and order_row.sell_id:
                order_row.sell_id.received_amount =\
                 sum([order.amount for order in self.search([('sell_id', '=',
                                                              order_row.sell_id.id),
                                                             ('state', '=', 'done')])])
        return return_vals



class money_invoice(models.Model):
    _inherit = 'money.invoice'


    move_id = fields.Many2one('wh.move', string=u'出入库单',
                              readonly=True, ondelete='cascade',
                              help=u'生成此发票的出入库单号')
