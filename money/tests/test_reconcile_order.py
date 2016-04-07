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
        # 首先新建对应的核销单
        # 新建adv_get_to_pay时，收款单、源单和核销单。    为了使用银行账户付款，先给银行账户收款
        bank_get = self.env['money.order'].create({'name': 'GET201601',
                                          'partner_id': self.env.ref('core.jd').id,
                                          'category_id': self.env.ref('money.core_category_sale').id,
                                          'date': '2016-04-07',
                                          'line_ids': [(0, 0, {'bank_id': self.env.ref('core.comm').id, 'amount': 400})],
                                          'type': 'get'
                                          })
        bank_get.money_order_done()
        order_adv_get_to_pay = self.env['money.order'].create({'name': 'PAY201601',
                                          'partner_id': self.env.ref('core.lenovo').id,
                                          'category_id': self.env.ref('money.core_category_purchase').id,
                                          'date': '2016-04-07',
                                          'line_ids': [(0, 0, {'bank_id': self.env.ref('core.comm').id, 'amount': 100})],
                                          'type': 'pay',
                                          })
        order_adv_get_to_pay.money_order_done()
        invoice_adv_get_to_pay = self.env['money.invoice'].create({'name': 'adv_get_to_pay_1',
                                          'partner_id': self.env.ref('core.lenovo').id,
                                          'category_id': self.env.ref('money.core_category_purchase').id,
                                          'date': '2016-04-07',
                                          'amount': 600.0,
                                          'reconciled': 0,
                                          'to_reconcile': 600.0})
        invoice_adv_get_to_pay.money_invoice_done()
        reconcile_adv_get_to_pay = self.env['reconcile.order'].create({'partner_id': self.env.ref('core.lenovo').id,
                                            'business_type': 'adv_get_to_pay',
                                            'name': 'TO20160005',
                                            'note': 'zxy adv_get_to_pay'})
        # 新建get_to_get时，源单和核销单
        invoice_get_to_get = self.env['money.invoice'].create({'name': 'get_to_get_1',
                                          'partner_id': self.env.ref('core.jd').id,
                                          'category_id': self.env.ref('money.core_category_sale').id,
                                          'date': '2016-04-07',
                                          'amount': 1000.0,
                                          'reconciled': 0,
                                          'to_reconcile': 1000.0})
        invoice_get_to_get.money_invoice_done()
        reconcile_get_to_get = self.env['reconcile.order'].create({'partner_id': self.env.ref('core.jd').id,
                                            'to_partner_id': self.env.ref('core.yixun').id,
                                            'business_type': 'get_to_get',
                                            'name': 'TO20160006',
                                            'note': 'zxy get to get'})
        # pay_to_pay，源单和核销单
        invoice_pay_to_pay = self.env['money.invoice'].create({'name': 'pay_to_pay_1',
                                          'partner_id': self.env.ref('core.jd').id,
                                          'category_id': self.env.ref('money.core_category_purchase').id,
                                          'date': '2016-04-07',
                                          'amount': 100.0,
                                          'reconciled': 0,
                                          'to_reconcile': 100.0})
        invoice_pay_to_pay.money_invoice_done()
        reconcile_pay_to_pay = self.env['reconcile.order'].create({'partner_id': self.env.ref('core.jd').id,
                                            'to_partner_id': self.env.ref('core.yixun').id,
                                            'business_type': 'pay_to_pay',
                                            'name': 'TO20160007',
                                            'note': 'zxy pay to pay'})
        for type in range(len(type_list)):
            if type == 0: # 执行 if# 预收冲应收
                reconcile = self.env.ref('money.adv_pay_to_get_2')
                reconcile.business_type = type_list[type]
                reconcile.onchange_partner_id()
                self.assertEqual(reconcile.business_type, type_list[type])
            if type == 1: # 执行 if# 预付冲应付
                reconcile = reconcile_adv_get_to_pay
                reconcile.business_type = type_list[type]
                reconcile.onchange_partner_id()
                self.assertEqual(reconcile.business_type, type_list[type])
            if type == 2: # 执行 if# 应收冲应付
                reconcile = self.env.ref('money.get_to_pay_1')
                reconcile.business_type = type_list[type]
                reconcile.onchange_partner_id()
                self.assertEqual(reconcile.business_type, type_list[type])
            if type == 3: # 执行 if#应收转应收
                reconcile = reconcile_get_to_get
                reconcile.business_type = type_list[type]
                reconcile.onchange_partner_id()
                self.assertEqual(reconcile.business_type, type_list[type])
            if type == 4: # 执行 if# 应付转应付
                reconcile = reconcile_pay_to_pay
                reconcile.business_type = type_list[type]
                reconcile.onchange_partner_id()
                self.assertEqual(reconcile.business_type, type_list[type])

        # 未审核的核销单可删除
        self.env.ref('money.get_to_pay_1').unlink()
        
        

