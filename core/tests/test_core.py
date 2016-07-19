# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from psycopg2 import IntegrityError
from openerp.exceptions import except_orm


class test_core(TransactionCase):

    def test_partner(self):
        ''' 测试删除已有客户的分类报错 '''
        return          # 测试已通过，但会在log里报ERROR，所以暂时去掉
        with self.assertRaises(IntegrityError):
            self.env.ref('core.customer_category_1').unlink()

    def test_res_currency(self):
        """测试阿拉伯数字转换称中文大写数字的方法"""
        self.env['res.currency'].rmb_upper(10000100.3)

    def test_miss_get_pricing_id(self):
    	'''测试定价侧率缺少输入的报错问题'''
    	partner = False
    	warehouse = self.env.ref('warehouse.hd_stock')
    	goods = self.env.ref('goods.mouse')
    	date = 20160101
    	pricing = self.env['pricing']
    	with self.assertRaises(except_orm):
    		pricing.get_pricing_id(partner, warehouse, goods, date)
    	partner = self.env.ref('core.zt')

    	warehouse = False
    	with self.assertRaises(except_orm):
    		pricing.get_pricing_id(partner, warehouse, goods, date)
    	warehouse = self.env.ref('warehouse.hd_stock')

    	goods = False
    	with self.assertRaises(except_orm):
    		pricing.get_pricing_id(partner, warehouse, goods, date)
    	goods = self.env.ref('goods.mouse')

    def test_good_pricing(self):
        '''测试good_pricing定价策略不唯一的情况'''
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
        print self.env['pricing'].search([
                                    ('c_category_id', '=', partner.c_category_id.id),
                                    ('warehouse_id', '=', warehouse.id),
                                    ('goods_id', '=', goods.id),
                                    ('goods_category_id', '=', False),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)
                                    ])
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
    
    def test_gc_pricing(self):
        '''测试gc_pricing定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.keyboard')
        date = 20160515
        gc_pricing = self.env['pricing'].search([
                                  ('c_category_id','=',partner.c_category_id.id),
                                  ('warehouse_id','=',warehouse.id),
                                  ('goods_id','=',False),
                                  ('goods_category_id','=',goods.category_id.id),
                                  ('active_date','<=',date),
                                  ('deactive_date','>=',date)
                                  ])
        cp = gc_pricing.copy()
        print self.env['pricing'].search([
                                  ('c_category_id','=',partner.c_category_id.id),
                                  ('warehouse_id','=',warehouse.id),
                                  ('goods_id','=',False),
                                  ('goods_category_id','=',goods.category_id.id),
                                  ('active_date','<=',date),
                                  ('deactive_date','>=',date)
                                  ])
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_pw_pricing(self):
        '''测试pw_pricing定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160615
        pw_pricing = self.env['pricing'].search([
                                  ('c_category_id','=',partner.c_category_id.id),
                                  ('warehouse_id','=',warehouse.id),
                                  ('goods_id','=',False),
                                  ('goods_category_id','=',False),
                                  ('active_date','<=',date),
                                  ('deactive_date','>=',date)
                                  ])
        cp = pw_pricing.copy()
        print self.env['pricing'].search([
                                  ('c_category_id','=',partner.c_category_id.id),
                                  ('warehouse_id','=',warehouse.id),
                                  ('goods_id','=',False),
                                  ('goods_category_id','=',False),
                                  ('active_date','<=',date),
                                  ('deactive_date','>=',date)
                                  ])
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_wg_pricing(self):
        '''测试wg_pricing定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160715
        wg_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',goods.id),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = wg_pricing.copy()
        print self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',goods.id),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
    
    def test_w_gc_pricing(self):
        '''测试w_gc_pricing定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160815
        w_gc_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',goods.category_id.id),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = w_gc_pricing.copy()
        print self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',goods.category_id.id),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
    
    def test_warehouse_pricing(self):
        '''测试warehouse_pricing定价策略不唯一的情况'''
        warehouse = self.env.ref('warehouse.bj_stock')
        date = 20160915
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        goods = self.env.ref('goods.mouse')
        warehouse_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = warehouse_pricing.copy()
        print self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
    
    def test_ccg_pricing(self):
        '''测试ccg_pricing定价策略不唯一的情况'''
        print '===here is ccg==='
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        goods = self.env.ref('goods.mouse')
        date = 20161015
        warehouse = self.env.ref('warehouse.bj_stock')
        ccg_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',goods.id),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = ccg_pricing.copy() 
        print self.env['pricing'].search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',goods.id),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
    
    def test_ccgc_pricing(self):
        '''测试ccgc_pricing定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20161115
        ccgc_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',goods.category_id.id),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = ccgc_pricing.copy()
        print self.env['pricing'].search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',goods.category_id.id),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_partner_pricing(self):
        '''测试partner_pricing定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20161215
        partner_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = partner_pricing.copy()
        print self.env['pricing'].search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_all_goods_pricing(self):
        '''测试partner_pricing定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20170101
        all_goods_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = all_goods_pricing.copy()
        print self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
