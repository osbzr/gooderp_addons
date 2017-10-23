# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Goods(models.Model):
    _inherit = 'goods'

    available_in_pos = fields.Boolean(string=u'可用于POS',
                                      help=u'如果你想这个商品适用于POS，勾选此项',
                                      default=True)
    to_weight = fields.Boolean(string=u'称重',
                               help=u"此商品是否需要使用称来称重")

    description_sale = fields.Text(string="to_weight")
    description = fields.Text(string="description")
    default_code = fields.Text(string="default_code")
    sequence = fields.Text(string="sequence")
