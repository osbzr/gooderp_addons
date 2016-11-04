# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class pricing(models.Model):
    _name = 'pricing'
    _description = u'定价策略'

    #此逻辑放在这里是为了让采购和销售都有机会使用价格策略，现在只在销售环节读取了这些策略

    @api.model
    def get_pricing_id(self, partner, warehouse, goods, date):
        '''传入客户，仓库，商品，日期，返回合适的价格策略，如果找到两条以上符合的规则，则报错
        1. 客户类别、仓库、商品
        2. 客户类别、仓库、商品类别
        3. 客户类别、仓库
        4. 仓库、商品
        5. 仓库，商品分类
        6. 仓库
        7. 客户类别、商品
        8. 客户类别、商品分类
        9. 客户类别
        10. 所有商品
        11. 可能还是找不到有效期内的，返回 False
        '''
        if not partner:
            raise UserError(u'请先输入客户')
        if not warehouse:
            raise UserError(u'请先输入仓库')
        if not goods:
            raise UserError(u'请先输入商品')
        # 客户类别、仓库、产品满足条件
        good_pricing = self.search([('c_category_id', '=', partner.c_category_id.id),
                                    ('warehouse_id', '=', warehouse.id),
                                    ('goods_id', '=', goods.id),
                                    ('goods_category_id', '=', False),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)
                                   ])
        # 客户类别、仓库、产品
        if len(good_pricing) == 1:
            return good_pricing
        if len(good_pricing) > 1:
            raise UserError(u'适用于%s,%s,%s,%s 的价格策略不唯一'
                            % (partner.c_category_id.name,
                               warehouse.name,
                               goods.name,
                               date))
        # 客户类别、仓库、产品类别满足条件
        gc_pricing = self.search([('c_category_id', '=', partner.c_category_id.id),
                                  ('warehouse_id', '=', warehouse.id),
                                  ('goods_id', '=', False),
                                  ('goods_category_id', '=', goods.category_id.id),
                                  ('active_date', '<=', date),
                                  ('deactive_date', '>=', date)
                                 ])
        # 客户类别、仓库、产品类别
        if len(gc_pricing) == 1:
            return gc_pricing
        if len(gc_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s,%s 的价格策略不唯一'
                            % (partner.c_category_id.name,
                               warehouse.name,
                               goods.category_id.name,
                               date))
        # 客户类别、仓库满足条件
        pw_pricing = self.search([('c_category_id', '=', partner.c_category_id.id),
                                  ('warehouse_id', '=', warehouse.id),
                                  ('goods_id', '=', False),
                                  ('goods_category_id', '=', False),
                                  ('active_date', '<=', date),
                                  ('deactive_date', '>=', date)
                                 ])
        # 客户类别、仓库
        if len(pw_pricing) == 1:
            return pw_pricing
        if len(pw_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s 的价格策略不唯一'
                            % (partner.c_category_id.name,
                               warehouse.name,
                               date))
        # 仓库、商品满足
        wg_pricing = self.search([('c_category_id', '=', False),
                                  ('warehouse_id', '=', warehouse.id),
                                  ('goods_id', '=', goods.id),
                                  ('goods_category_id', '=', False),
                                  ('active_date', '<=', date),
                                  ('deactive_date', '>=', date)
                                 ])
        # 仓库、商品
        if len(wg_pricing) == 1:
            return wg_pricing
        if len(wg_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s 的价格策略不唯一'
                            % (warehouse.name,
                               goods.name,
                               date))
        # 仓库，商品分类满足条件
        w_gc_pricing = self.search([('c_category_id', '=', False),
                                    ('warehouse_id', '=', warehouse.id),
                                    ('goods_id', '=', False),
                                    ('goods_category_id', '=',
                                     goods.category_id.id),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)
                                   ])
        # 仓库，商品分类
        if len(w_gc_pricing) == 1:
            return w_gc_pricing
        if len(w_gc_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s 的价格策略不唯一' % (warehouse.name,
                                                        goods.category_id.name,
                                                        date))
        # 仓库满足条件
        warehouse_pricing = self.search([
            ('c_category_id', '=', False),
            ('warehouse_id', '=', warehouse.id),
            ('goods_id', '=', False),
            ('goods_category_id', '=', False),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        # 仓库
        if len(warehouse_pricing) == 1:
            return warehouse_pricing
        if len(warehouse_pricing) > 1:
            raise UserError(u'适用于 %s,%s 的价格策略不唯一' % (warehouse.name,
                                                     date))
        # 客户类别,商品满足条件
        ccg_pricing = self.search([
            ('c_category_id', '=', partner.c_category_id.id),
            ('warehouse_id', '=', False),
            ('goods_id', '=', goods.id),
            ('goods_category_id', '=', False),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        # 客户类别,商品
        if len(ccg_pricing) == 1:
            return ccg_pricing
        if len(ccg_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                                        goods.name,
                                                        date))
        # 客户类别,产品分类满足条件
        ccgc_pricing = self.search([
            ('c_category_id', '=', partner.c_category_id.id),
            ('warehouse_id', '=', False),
            ('goods_id', '=', False),
            ('goods_category_id', '=',
             goods.category_id.id),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        # 客户类别，产品分类
        if len(ccgc_pricing) == 1:
            return ccgc_pricing
        if len(ccgc_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                                        goods.category_id.name,
                                                        date))
        # 客户类别满足条件
        partner_pricing = self.search([('c_category_id', '=', partner.c_category_id.id),
                                       ('warehouse_id', '=', False),
                                       ('goods_id', '=', False),
                                       ('goods_category_id', '=', False),
                                       ('active_date', '<=', date),
                                       ('deactive_date', '>=', date)
                                      ])
        # 客户类别
        if len(partner_pricing) == 1:
            return partner_pricing
        if len(partner_pricing) > 1:
            raise UserError(u'适用于 %s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                                     date))
        # 所有产品打折
        all_goods_pricing = self.search([
            ('c_category_id', '=', False),
            ('warehouse_id', '=', False),
            ('goods_id', '=', False),
            ('goods_category_id', '=', False),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        # 所有产品
        if len(all_goods_pricing) == 1:
            return all_goods_pricing
        if len(all_goods_pricing) > 1:
            raise UserError(u'适用于 %s 的价格策略不唯一' % (date))
        # 如果日期范围内没有适用的价格策略，则返回空
        if len(good_pricing) + len(gc_pricing) + len(pw_pricing) + len(wg_pricing)\
                + len(w_gc_pricing) + len(warehouse_pricing) + len(ccg_pricing)\
                + len(partner_pricing) + len(all_goods_pricing) == 0:
            return False

    name = fields.Char(u'描述', help=u'描述!')
    warehouse_id = fields.Many2one('warehouse', u'仓库')
    c_category_id = fields.Many2one('core.category', u'客户类别',
                                    ondelete='restrict',
                                    domain=[('type', '=', 'customer')],
                                    context={'type': 'customer'})
    goods_category_id = fields.Many2one('core.category', u'产品类别',
                                        ondelete='restrict',
                                        domain=[('type', '=', 'goods')],
                                        context={'type': 'goods'})
    goods_id = fields.Many2one('goods', u'产品')
    active_date = fields.Date(u'开始日期', required=True)
    deactive_date = fields.Date(u'终止日期', required=True)
    discount_rate = fields.Float(u'折扣率%', help=u'产品的价格 × 折扣率 = 产品的实际价格 !')