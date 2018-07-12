# -*- coding: utf-8 -*-

from odoo import models, fields


class sell_order_line(models.Model):
    _inherit = "sell.order.line"

    is_bought = fields.Boolean(u'已采购', copy=False, readonly=True)
