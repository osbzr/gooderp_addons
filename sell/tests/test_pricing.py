# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestPricing(TransactionCase):

    def test_miss_get_pricing_id(self):
        '''测试定价策略缺少输入的报错问题'''
        warehouse = self.env.ref('warehouse.hd_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160101
        partner = self.env.ref('core.zt')
        pricing = self.env['pricing']
        with self.assertRaises(UserError):
            pricing.get_pricing_id(False, warehouse, goods, date)

        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, False, goods, date)

        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, False, date)

    def test_good_pricing(self):
        '''测试定价输入商品名称、仓库、客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160415
        good_pricing = self.env['pricing'].search([
            ('c_category_id', '=', partner.c_category_id.id),
            ('warehouse_id', '=', warehouse.id),
            ('goods_id', '=', goods.id),
            ('goods_category_id', '=', False),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        cp = good_pricing.copy()
        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_gc_pricing(self):
        '''测试定价输入商品类别、仓库、客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.keyboard')
        date = 20160515
        gc_pricing = self.env['pricing'].search([
            ('c_category_id', '=', partner.c_category_id.id),
            ('warehouse_id', '=', warehouse.id),
            ('goods_id', '=', False),
            ('goods_category_id', '=', goods.category_id.id),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        cp = gc_pricing.copy()
        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_pw_pricing(self):
        '''测试定价输入仓库、客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160615
        pw_pricing = self.env['pricing'].search([
            ('c_category_id', '=', partner.c_category_id.id),
            ('warehouse_id', '=', warehouse.id),
            ('goods_id', '=', False),
            ('goods_category_id', '=', False),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        cp = pw_pricing.copy()
        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_wg_pricing(self):
        '''测试定价输入商品名称、仓库、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160715
        wg_pricing = self.env['pricing'].search([
            ('c_category_id', '=', False),
            ('warehouse_id', '=', warehouse.id),
            ('goods_id', '=', goods.id),
            ('goods_category_id', '=', False),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        cp = wg_pricing.copy()
        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_w_gc_pricing(self):
        '''测试定价输入商品类别、仓库、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160815
        w_gc_pricing = self.env['pricing'].search([
            ('c_category_id', '=', False),
            ('warehouse_id', '=', warehouse.id),
            ('goods_id', '=', False),
            ('goods_category_id', '=',
             goods.category_id.id),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        cp = w_gc_pricing.copy()
        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_warehouse_pricing(self):
        '''测试定价输入仓库、日期时，定价策略不唯一的情况'''
        warehouse = self.env.ref('warehouse.bj_stock')
        date = 20160915
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        goods = self.env.ref('goods.mouse')
        warehouse_pricing = self.env['pricing'].search([
            ('c_category_id', '=', False),
            ('warehouse_id', '=', warehouse.id),
            ('goods_id', '=', False),
            ('goods_category_id', '=', False),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        cp = warehouse_pricing.copy()
        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_ccg_pricing(self):
        '''测试定价输入商品名称、客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        goods = self.env.ref('goods.mouse')
        date = 20161015
        warehouse = self.env.ref('warehouse.bj_stock')
        ccg_pricing = self.env['pricing'].search([
            ('c_category_id', '=', partner.c_category_id.id),
            ('warehouse_id', '=', False),
            ('goods_id', '=', goods.id),
            ('goods_category_id', '=', False),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        cp = ccg_pricing.copy()
        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_ccgc_pricing(self):
        '''测试定价输入商品类别、客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20161115
        ccgc_pricing = self.env['pricing'].search([
            ('c_category_id', '=', partner.c_category_id.id),
            ('warehouse_id', '=', False),
            ('goods_id', '=', False),
            ('goods_category_id', '=',
             goods.category_id.id),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        cp = ccgc_pricing.copy()
        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_partner_pricing(self):
        '''测试定价输入客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20161215
        partner_pricing = self.env['pricing'].search([
            ('c_category_id', '=', partner.c_category_id.id),
            ('warehouse_id', '=', False),
            ('goods_id', '=', False),
            ('goods_category_id', '=', False),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        cp = partner_pricing.copy()
        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_all_goods_pricing(self):
        '''测试定价只输入日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20170101
        all_goods_pricing = self.env['pricing'].search([
            ('c_category_id', '=', False),
            ('warehouse_id', '=', False),
            ('goods_id', '=', False),
            ('goods_category_id', '=', False),
            ('active_date', '<=', date),
            ('deactive_date', '>=', date)
        ])
        cp = all_goods_pricing.copy()
        with self.assertRaises(UserError):
            pricing.get_pricing_id(partner, warehouse, goods, date)
