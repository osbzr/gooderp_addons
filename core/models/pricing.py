# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class pricing(models.Model):
    _name = 'pricing'
    _description = u'定价策略'

    #此逻辑放在这里是为了让采购和销售都有机会使用价格策略，现在只在销售环节读取了这些策略

    def get_condition(self, partner, warehouse, goods, date):
        '''返回定价策略的各种条件及报错信息'''
        # 客户类别、仓库、商品满足条件
        message = (u'适用于%s,%s,%s,%s 的价格策略不唯一'
                   % (partner.c_category_id.name,
                      warehouse.name,
                      goods.name,
                      date))
        res = {'good_pricing': {'domain': [('c_category_id', '=', partner.c_category_id.id),
                                           ('warehouse_id', '=', warehouse.id),
                                           ('goods_id', '=', goods.id),
                                           ('goods_category_id', '=', False),
                                           ('active_date', '<=', date),
                                           ('deactive_date', '>=', date)],
                                'message': message}}
        # 客户类别、仓库、商品类别满足条件
        message = (u'适用于 %s,%s,%s,%s 的价格策略不唯一'
                   % (partner.c_category_id.name,
                      warehouse.name,
                      goods.category_id.name,
                      date))
        res.update({'gc_pricing':
                        {'domain': [('c_category_id', '=', partner.c_category_id.id),
                                    ('warehouse_id', '=', warehouse.id),
                                    ('goods_id', '=', False),
                                    ('goods_category_id', '=', goods.category_id.id),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)],
                         'message': message}})
        # 客户类别、仓库满足条件
        message = (u'适用于 %s,%s,%s 的价格策略不唯一'
                   % (partner.c_category_id.name,
                      warehouse.name,
                      date))
        res.update({'pw_pricing':
                        {'domain': [('c_category_id', '=', partner.c_category_id.id),
                                    ('warehouse_id', '=', warehouse.id),
                                    ('goods_id', '=', False),
                                    ('goods_category_id', '=', False),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)],
                         'message': message}})
        # 仓库、商品满足
        message = (u'适用于 %s,%s,%s 的价格策略不唯一'
                   % (warehouse.name,
                      goods.name,
                      date))
        res.update({'wg_pricing':
                        {'domain': [('c_category_id', '=', False),
                                    ('warehouse_id', '=', warehouse.id),
                                    ('goods_id', '=', goods.id),
                                    ('goods_category_id', '=', False),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)],
                         'message': message}})
        # 仓库，商品分类满足条件
        message = (u'适用于 %s,%s,%s 的价格策略不唯一' % (warehouse.name,
                                               goods.category_id.name,
                                               date))
        res.update({'w_gc_pricing':
                        {'domain': [('c_category_id', '=', False),
                                    ('warehouse_id', '=', warehouse.id),
                                    ('goods_id', '=', False),
                                    ('goods_category_id', '=',
                                     goods.category_id.id),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)],
                         'message': message}})
        # 仓库满足条件
        message = (u'适用于 %s,%s 的价格策略不唯一' % (warehouse.name,
                                            date))
        res.update({'warehouse_pricing':
                        {'domain': [('c_category_id', '=', False),
                                    ('warehouse_id', '=', warehouse.id),
                                    ('goods_id', '=', False),
                                    ('goods_category_id', '=', False),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)],
                         'message': message}})
        # 客户类别,商品满足条件
        message = (u'适用于 %s,%s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                               goods.name,
                                               date))
        res.update({'ccg_pricing':
                        {'domain': [('c_category_id', '=', partner.c_category_id.id),
                                    ('warehouse_id', '=', False),
                                    ('goods_id', '=', goods.id),
                                    ('goods_category_id', '=', False),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)],
                         'message': message}})
        # 客户类别,商品分类满足条件
        message = (u'适用于 %s,%s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                               goods.category_id.name,
                                               date))
        res.update({'ccgc_pricing':
                        {'domain': [('c_category_id', '=', partner.c_category_id.id),
                                    ('warehouse_id', '=', False),
                                    ('goods_id', '=', False),
                                    ('goods_category_id', '=',
                                     goods.category_id.id),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)],
                         'message': message}})
        # 客户类别满足条件
        message = (u'适用于 %s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                            date))
        res.update({'partner_pricing':
                        {'domain': [('c_category_id', '=', partner.c_category_id.id),
                                    ('warehouse_id', '=', False),
                                    ('goods_id', '=', False),
                                    ('goods_category_id', '=', False),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)],
                         'message': message}})
        # 所有商品打折
        message = (u'适用于 %s 的价格策略不唯一' % (date))
        res.update({'all_goods_pricing':
                        {'domain': [('c_category_id', '=', False),
                                    ('warehouse_id', '=', False),
                                    ('goods_id', '=', False),
                                    ('goods_category_id', '=', False),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)],
                         'message': message}})
        return res

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
        res = self.get_condition(partner, warehouse, goods, date)
        sum = 0
        for k, value in res.items():
            pricing = self.search(value['domain'])
            if len(pricing) == 1:
                return pricing
            if len(pricing) > 1:
                raise UserError(value['message'])
            sum += len(pricing)
        # 如果日期范围内没有适用的价格策略，则返回空
        if sum == 0:
            return False

    name = fields.Char(u'描述', help=u'描述!')
    warehouse_id = fields.Many2one('warehouse',
                                   u'仓库',
                                   ondelete = 'restrict',
                                   )
    c_category_id = fields.Many2one('core.category', u'客户类别',
                                    ondelete='restrict',
                                    domain=[('type', '=', 'customer')],
                                    context={'type': 'customer'})
    goods_category_id = fields.Many2one('core.category', u'商品类别',
                                        ondelete='restrict',
                                        domain=[('type', '=', 'goods')],
                                        context={'type': 'goods'})
    goods_id = fields.Many2one('goods',
                               u'商品',
                               ondelete='restrict',
                               )
    active_date = fields.Date(u'开始日期', required=True)
    deactive_date = fields.Date(u'终止日期', required=True)
    discount_rate = fields.Float(u'折扣率%', help=u'商品的价格 × 折扣率 = 商品的实际价格 !')
