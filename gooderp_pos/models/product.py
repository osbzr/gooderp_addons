# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class goods(models.Model):
    _inherit = 'goods'

    available_in_pos = fields.Boolean(string='Available in the Point of Sale', help='Check if you want this product to appear in the Point of Sale', default=True)
    to_weight = fields.Boolean(string='To Weigh With Scale', help="Check if the product should be weighted using the hardware scale integration")
    pos_categ_id = fields.Many2one(
        'pos.category', string='Point of Sale Category',
        help="Those categories are used to group similar products for point of sale.")

    description_sale = fields.Text(string="to_weight")
    name = fields.Text(string="name")
    description = fields.Text(string="description")
    default_code = fields.Text(string="default_code")
    sequence = fields.Text(string="sequence")