# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from psycopg2 import IntegrityError


class test_core(TransactionCase):
    
    def test_partner(self):
        ''' 测试删除已有客户的分类报错 '''
        with self.assertRaises(IntegrityError):
            self.env.ref('core.customer_category_1').unlink()
