# -*- coding: utf-8 -*-
from odoo import models, fields, api


class location(models.Model):
    _name = 'location'
    _description = u'货位'
    _order = 'name'

    @api.multi
    def _get_current_qty(self):
        # 获取当前 库位 的商品数量
        for location in self:
            lines = self.env['wh.move.line'].search([('goods_id', '=', location.goods_id.id),
                                                    ('attribute_id', '=', location.attribute_id.id),
                                                    ('warehouse_dest_id', '=', location.warehouse_id.id),
                                                    ('location_id', '=', location.id),
                                                    ('state', '=', 'done')])
            location.current_qty = sum([line.qty_remaining for line in lines])
            if location.current_qty == 0:
                location.goods_id = False
                location.attribute_id = False

    name = fields.Char(u'货位号',
                       required=True)
    warehouse_id = fields.Many2one('warehouse',
                                   string=u'仓库',
                                   required=True)
    goods_id = fields.Many2one('goods',
                               u'商品')
    attribute_id = fields.Many2one('attribute', u'属性', ondelete='restrict',
                                   help=u'商品的属性')
    current_qty = fields.Integer(u'数量',
                                 compute='_get_current_qty')

    _sql_constraints = [
        ('wh_loc_uniq', 'unique(warehouse_id, name)', u'同仓库库位不能重名')
    ]
