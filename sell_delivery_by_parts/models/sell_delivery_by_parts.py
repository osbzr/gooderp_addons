# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class Goods(models.Model):
    _inherit = 'goods'

    is_assembly_sell = fields.Boolean(u'组装销售')


class WhMoveLine(models.Model):
    _inherit = 'wh.move.line'

    @api.model
    def create(self, vals):
        ''' 组合产品生成子产品的发货单行 '''
        goods = self.env['goods'].search([('id', '=', vals['goods_id'])])
        bom_line_obj = self.env['wh.bom.line']

        if not goods.is_assembly_sell:
            return super(WhMoveLine, self).create(vals)
        else:
            # 如果是组合产品，查找对应子产品
            bom_line_parent = bom_line_obj.search([('goods_id', '=', goods.id),
                                                   ('bom_id.type', '=', 'assembly'),
                                                   ('attribute_id', '=', vals.get('attribute_id')),
                                                   ('type', '=', 'parent')])
            if not bom_line_parent:
                raise UserError(u'请先建立组合销售产品%s的物料清单！' % goods.name)
            bom_line_child = bom_line_obj.search([('bom_id', '=', bom_line_parent.bom_id.id),
                                                  ('bom_id.type', '=', 'assembly'),
                                                  ('type', '=', 'child')])
            price_sum = 0 # 加权平均的除数
            for child in bom_line_child:
                price_sum += child.goods_qty * child.goods_id.price
            new_line_id = False
            for child in bom_line_child:
                child_vals = vals.copy()
                child_vals['goods_id'] = child.goods_id.id
                child_vals['attribute_id'] = child.attribute_id.id
                child_vals['goods_qty'] = vals['goods_qty'] * child.goods_qty
                if vals.get('price_taxed') and price_sum:
                    child_vals['price_taxed'] = child.goods_id.price * vals['price_taxed'] / price_sum
                else:
                    child_vals['price_taxed'] = 0

                # 多次调用 create 方法，但只返回最后一次调用的值
                new_line_id = self.create(child_vals)
            return new_line_id
