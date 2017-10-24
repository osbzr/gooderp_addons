# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class ProductStyle(models.Model):
    _name = "product.style"
    _description = u'产品样式'

    name = fields.Char(string=u'产品',
                       required=True)
    html_class = fields.Char(string='HTML Classes')


class Goods(models.Model):
    _inherit = ['goods', 'website.published.mixin']
    _name = 'goods'

    website_size_x = fields.Integer('Size X',
                                    default=1)
    website_size_y = fields.Integer('Size Y',
                                    default=1)
    website_style_ids = fields.Many2many('product.style',
                                         string=u'样式')
