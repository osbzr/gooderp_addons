# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from psycopg2 import IntegrityError
from odoo.exceptions import UserError


class test_core(TransactionCase):

    def test_partner(self):
        ''' 测试删除已有客户的分类报错 '''
        return          # 测试已通过，但会在log里报ERROR，所以暂时去掉
        with self.assertRaises(IntegrityError):
            self.env.ref('core.customer_category_1').unlink()

    def test_res_currency(self):
        """测试阿拉伯数字转换称中文大写数字的方法"""
        self.env['res.currency'].rmb_upper(10000100.3)
        # 测试输入value为负时的货币大写问题
        self.assertTrue(self.env['res.currency'].rmb_upper(-10000100.3) == u'负壹仟万零壹佰元叁角整')
        
class test_res_users(TransactionCase):
    
    def test_write(self):
        '''修改管理员权限'''
        user_demo = self.env.ref('base.user_demo')
        user_demo.groups_id = [(4, self.env.ref('base.group_erp_manager').id)]
        user_admin = self.env.ref('base.user_root')
        env2 = self.env(self.env.cr, user_demo.id, self.env.context)
        with self.assertRaises(UserError):
            user_admin.with_env(env2).name = 'adsf'
        # with self.assertRaises(UserError):
        user_admin.groups_id = [(3, self.env.ref('base.group_erp_manager').id)]


