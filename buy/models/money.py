
from odoo import fields, models, api


class CostLine(models.Model):
    _inherit = 'cost.line'

    buy_id = fields.Many2one('buy.receipt', '入库单号', ondelete='cascade',
                             help='与采购费用关联的入库单号')


class MoneyOrder(models.Model):
    _inherit = 'money.order'

    buy_id = fields.Many2one('buy.order', '采购订单', ondelete='restrict',
                             help='与付款相关的采购订单号')


class MoneyInvoice(models.Model):
    _inherit = 'money.invoice'

    move_id = fields.Many2one('wh.move', string='出入库单',
                              readonly=True, ondelete='cascade',
                              help='生成此发票的出入库单号')
