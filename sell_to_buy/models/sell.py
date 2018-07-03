# -*- coding: utf-8 -*-

from odoo import models, fields


class sell_order_line(models.Model):
    _inherit = "sell.order.line"

    buy_line_id = fields.Many2one('buy.order.line',
                                  u'购货单行',
                                  help=u'对应的购货订单行')
    is_bought = fields.Boolean(u'已采购')







