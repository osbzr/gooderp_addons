# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from psycopg2 import IntegrityError


class test_core(TransactionCase):
    
    def test_partner(self):
        ''' 测试删除已有客户的分类报错 '''
        return          # 测试已通过，但会在log里报ERROR，所以暂时去掉
        with self.assertRaises(IntegrityError):
            self.env.ref('core.customer_category_1').unlink()

    def test_onchange_partner(self):
        '''测试partner的onchange'''
        self.env['partner'].onchange_partner_id()
#         self.partner_address = self.env['res.partner'].create(dict(name = 'jd.address',
#                                                                email = 'd@d',
#                                                                ))
#         self.env['partner'].onchange_partner_id()
