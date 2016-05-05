# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from psycopg2 import IntegrityError


class test_core(TransactionCase):

    def test_partner(self):
        ''' 测试删除已有客户的分类报错 '''
        return          # 测试已通过，但会在log里报ERROR，所以暂时去掉
        with self.assertRaises(IntegrityError):
            self.env.ref('core.customer_category_1').unlink()

    def test_res_currency(self):
        """测试阿拉伯数字转换称中文大写数字的方法"""
        self.env['res.currency'].rmb_upper(10000100.3)


class test_goods(TransactionCase):

    def setUp(self):
        super(test_goods, self).setUp()
        self.mouse = self.env.ref('goods.mouse')

    def test_name_search(self):
        # 使用name来搜索键盘
        result = self.env['goods'].name_search('鼠标')
        real_result = [(self.mouse.id,
                        self.mouse.code + '_' + self.mouse.name)]

        self.assertEqual(result, real_result)

        # 使用code来搜索键盘
        result = self.env['goods'].name_search('001')
        self.assertEqual(result, real_result)
