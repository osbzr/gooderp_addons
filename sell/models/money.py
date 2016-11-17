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
