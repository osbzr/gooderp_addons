# -*- coding: utf-8 -*-
from odoo import models, fields

class location(models.Model):
    _name = 'location'
    _description = u'货位'
    
    name = fields.Char(u'货位号',
                       required=True)
    warehouse_id = fields.Many2one('warehouse',
                                   string='仓库',
                                   required=True)
    goods_id = fields.Many2one('goods',
                               u'商品')
