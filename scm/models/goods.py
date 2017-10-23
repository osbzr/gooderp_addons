# -*- coding: utf-8 -*-

from odoo import models, fields
import odoo.addons.decimal_precision as dp


class Goods(models.Model):
    _inherit = 'goods'

    min_stock_qty = fields.Float(u'最低库存量', digits=dp.get_precision('Quantity'))
