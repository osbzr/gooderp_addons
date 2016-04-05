# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_reconcile_order(TransactionCase):
    def test_reconcile_order(self):
        '''测试核销单的创建和删除'''
        # 核销单审核
        self.env.ref('money.get_to_pay_1').reconcile_order_done()
        '''
        self.env.ref('money.adv_pay_to_get_2').reconcile_order_done()
        # 确认核销单为已审核状态
        self.assertEqual(self.env.ref('money.adv_pay_to_get_2').state, 'done')
        '''
        # 已审核的核销单应该不可删除
        with self.assertRaises(except_orm):
            self.env.ref('money.get_to_pay_1').unlink()