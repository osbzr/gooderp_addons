# -*- encoding: utf-8 -*-

from odoo import fields, models, api


class cost_line(models.Model):
    _inherit = 'cost.line'

    sell_id = fields.Many2one('sell.delivery', u'出库单号',
                              ondelete='cascade',
                              help=u'与销售费用相关联的出库单号')


class money_invoice(models.Model):
    _inherit = 'money.invoice'


    move_id = fields.Many2one('wh.move', string=u'出入库单',
                              readonly=True, ondelete='cascade',
                              help=u'生成此发票的出入库单号')

class money_order(models.Model):
    _inherit = 'money.order'

    @api.multi
    def money_order_done(self):
        ''' 将已核销金额写回到销货订单中的已执行金额 '''
        self.ensure_one()
        res = super(money_order, self).money_order_done()
        move = False
        for source in self.source_ids:
            if self.type == 'get':
                move = self.env['sell.delivery'].search(
                    [('invoice_id', '=', source.name.id)])
                if move.order_id:
                    move.order_id.amount_executed = abs(source.name.reconciled)
        return res

    @api.multi
    def money_order_draft(self):
        ''' 将销货订单中的已执行金额清零'''
        self.ensure_one()
        res = super(money_order, self).money_order_draft()
        move = False
        for source in self.source_ids:
            if self.type == 'get':
                move = self.env['sell.delivery'].search(
                    [('invoice_id', '=', source.name.id)])
                if move.order_id:
                    move.order_id.amount_executed = 0
        return res
