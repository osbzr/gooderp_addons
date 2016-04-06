# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_reconcile_order(TransactionCase):
    def test_reconcile_order(self):
        '''测试核销单的创建和删除'''
        # 核销单审核
        self.env.ref('money.adv_pay_to_get_2').reconcile_order_done()
        # 确认核销单为已审核状态
        self.assertEqual(self.env.ref('money.adv_pay_to_get_2').state, 'done')
        # 已审核的核销单应该不可删除
        with self.assertRaises(except_orm):
            self.env.ref('money.adv_pay_to_get_2').unlink()
        # 未审核的核销单可删除
        self.env.ref('money.get_to_pay_1').unlink()
        
        # onchange_partner_id改变partner_id
        self.partner_id = self.env.ref('core.jd').id
        self.env['reconcile.order'].onchange_partner_id()
        self.assertEqual(self.partner_id, self.env.ref('core.jd').id)
        # onchange_partner_id改变为空
        self.partner_id = False
        self.env['reconcile.order'].onchange_partner_id()
        self.assertEqual(self.partner_id, False)
        # onchange_partner_id改变business_type
        type_list = ['adv_pay_to_get', 'adv_get_to_pay', 'get_to_pay', 'get_to_get', 'pay_to_pay', '']
        for type in range(len(type_list)):
            self.business_type = type_list[type]
            self.env['reconcile.order'].onchange_partner_id()
            self.assertEqual(self.business_type, type_list[type])
        
        

