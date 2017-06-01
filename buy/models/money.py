# -*- coding: utf-8 -*-

from odoo import fields, models, api


class cost_line(models.Model):
    _inherit = 'cost.line'

    buy_id = fields.Many2one('buy.receipt', u'入库单号', ondelete='cascade',
                             help=u'与采购费用关联的入库单号')

class money_order(models.Model):
    _inherit = 'money.order'

    buy_id = fields.Many2one('buy.order', u'采购订单', ondelete='restrict',
                             help=u'与付款相关的采购订单号')

    @api.multi
    def money_order_done(self):
        """当 付款单审核后重新计算"""
        return_vals = super(money_order, self).money_order_done()
        for order_row in self:
            if order_row.type == 'pay' and order_row.buy_id:
                order_row.buy_id.paid_amount =\
                 sum([order.amount for order in self.search([('buy_id', '=',
                                                              order_row.buy_id.id),
                                                             ('state', '=', 'done')])])
        return return_vals

    @api.multi
    def money_order_draft(self):
        """当 付款单审核后重新计算"""
        return_vals = super(money_order, self).money_order_draft()
        for order_row in self:
            if order_row.type == 'pay' and order_row.buy_id:
                order_row.buy_id.paid_amount =\
                 sum([order.amount for order in self.search([('buy_id', '=',
                                                              order_row.buy_id.id),
                                                             ('state', '=', 'done')])])
        return return_vals


class money_invoice(models.Model):
    _inherit = 'money.invoice'

    move_id = fields.Many2one('wh.move', string=u'出入库单',
                              readonly=True, ondelete='cascade',
                              help=u'生成此发票的出入库单号')
