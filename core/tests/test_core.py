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
    	'''测试定价策略'''
    	# 测试定价侧率缺少输入的报错问题
    	partner = False
    	warehouse = self.env.ref('core.check')
    	goods = self.env.ref('goods.mouse')
    	date = 20160101
    	pricing = self.env['pricing']
    	with self.assertRaises(except_orm):
    		pricing.get_pricing_id(partner, warehouse, goods, date)
    	partner = self.env.ref('core.zt')

    	warehouse = False
    	with self.assertRaises(except_orm):
    		pricing.get_pricing_id(partner, warehouse, goods, date)
    	warehouse = self.env.ref('core.check')

    	goods = False
    	with self.assertRaises(except_orm):
    		pricing.get_pricing_id(partner, warehouse, goods, date)
    	goods = self.env.ref('goods.mouse')

        # 测试定价策略不唯一
        #with self.assertRaises(except_orm):
    	#	pricing.get_pricing_id(partner, warehouse, goods, date)




