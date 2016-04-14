# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class test_core(TransactionCase):
    
    def test_partner(self):
        ''' 测试删除已有客户的分类报错 '''
        with self.assertRaises(except_orm):
            self.env.ref('core.customer_category_1').unlink()
