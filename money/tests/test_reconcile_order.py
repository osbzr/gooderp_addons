# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestReconcileOrder(TransactionCase):

    def setUp(self):
        super(TestReconcileOrder, self).setUp()
        # 给core.comm收一笔款
        self.money_get_40000 = self.env.ref(
            'money.get_40000').money_order_done()
        self.get_invoice = self.env['money.invoice'].create({'partner_id': self.env.ref('core.jd').id,
                                                             'name': 'invoice/201600661', 'date': "2016-02-20",
                                                             'category_id': self.env.ref('money.core_category_sale').id,
                                                             'amount': 300.0,
                                                             'reconciled': 0,
                                                             'to_reconcile': 300.0})
        self.pay_invoice = self.env['money.invoice'].create({'name': 'pay_invoice', 'date': "2016-02-20",
                                                             'partner_id': self.env.ref('core.lenovo').id,
                                                             'category_id': self.env.ref('money.core_category_purchase').id,
                                                             'amount': 600.0,
                                                             'reconciled': 0,
                                                             'to_reconcile': 600.0})

    def test_money_invoice_done(self):
        # money.invoice 没有设置科目 银行账户没设置科目
        self.get_invoice.partner_id.receivable = 0
        c_category_id = self.get_invoice.partner_id.c_category_id.id
        self.get_invoice.partner_id.s_category_id = self.env.ref('core.supplier_category_1').id
        self.get_invoice.category_id.account_id = False
        self.get_invoice.partner_id.c_category_id = c_category_id
        with self.assertRaises(UserError):
            # 结算单类别找不到科目
            self.get_invoice.money_invoice_done()

    def test_adv_pay_to_get(self):
        '''测试核销单: 预收冲应收'''
        reconcile = self.env.ref('money.reconcile_adv_pay_to_get')
        reconcile.partner_id = self.env.ref('core.jd').id
        reconcile.onchange_partner_id()
        reconcile.advance_payment_ids.this_reconcile = 300.0
        reconcile.receivable_source_ids[0].this_reconcile = 300.0
        reconcile.reconcile_order_done()

    def test_adv_get_to_pay(self):
        '''测试核销单: 预付冲应付'''
        self.env.ref('money.pay_2000').money_order_done()
        reconcile = self.env.ref('money.reconcile_adv_get_to_pay')
        reconcile.partner_id = self.env.ref('core.lenovo').id
        reconcile.onchange_partner_id()
        reconcile.advance_payment_ids.this_reconcile = 600.0
        reconcile.payable_source_ids[0].this_reconcile = 700.0
        # 核销金额不能大于未核销金额。\n核销金额:700 未核销金额:600
        with self.assertRaises(UserError):
            reconcile.reconcile_order_done()

        reconcile.payable_source_ids[0].this_reconcile = 600.0
        reconcile.reconcile_order_done()

    def test_get_to_pay(self):
        '''测试核销单: 应收冲应付'''
        self.env.ref('money.pay_2000').money_order_done()
        self.get_invoice.partner_id = self.env.ref('core.lenovo').id
        reconcile = self.env.ref('money.reconcile_get_to_pay')
        reconcile.partner_id = self.env.ref('core.lenovo').id
        reconcile.onchange_partner_id()
        reconcile.payable_source_ids[0].this_reconcile = 300.0
        reconcile.reconcile_order_done()

    def test_get_to_get(self):
        '''测试核销单: 应收转应收'''
        reconcile = self.env.ref('money.reconcile_get_to_get')
        reconcile.partner_id = self.env.ref('core.jd').id
        reconcile.onchange_partner_id()
        reconcile.receivable_source_ids.this_reconcile = 300.0
        reconcile.reconcile_order_done()

    def test_pay_to_pay(self):
        '''测试核销单: 应付转应付'''
        self.get_invoice.partner_id = self.env.ref('core.lenovo').id
        reconcile = self.env.ref('money.reconcile_pay_to_pay')
        reconcile.partner_id = self.env.ref('core.lenovo').id
        reconcile.onchange_partner_id()
        reconcile.payable_source_ids[0].this_reconcile = 600.0
        reconcile.reconcile_order_done()

    def test_reconcile_order(self):
        '''核销单审核reconcile_order_done()'''
        reconcile = self.env.ref('money.reconcile_adv_pay_to_get')
        reconcile.partner_id = self.env.ref('core.jd').id
        reconcile.onchange_partner_id()
        # 核销金额不能大于未核销金额
        reconcile.advance_payment_ids.to_reconcile = 200.0
        with self.assertRaises(UserError):
            reconcile.reconcile_order_done()
        reconcile.receivable_source_ids.to_reconcile = 200.0
        with self.assertRaises(UserError):
            reconcile.reconcile_order_done()
        reconcile.advance_payment_ids.to_reconcile = 300.0
        reconcile.receivable_source_ids.to_reconcile = 300.0
        reconcile.advance_payment_ids.this_reconcile = 300.0
        reconcile.receivable_source_ids.this_reconcile = 300.0
        reconcile.reconcile_order_done()
        # 确认核销单为已审核状态
        self.assertEqual(reconcile.state, 'done')
        # 已审核的核销单应该不可删除
        with self.assertRaises(UserError):
            reconcile.unlink()
        # 未审核的核销单可删除
        self.env.ref('money.pay_2000').money_order_done()
        reconcile = self.env.ref('money.reconcile_get_to_pay')
        reconcile.partner_id = self.env.ref('core.lenovo').id
        reconcile.unlink()
        # 核销金额必须相同
        reconcile_adv_get_to_pay = self.env.ref(
            'money.reconcile_adv_get_to_pay')
        reconcile_adv_get_to_pay.partner_id = self.env.ref('core.lenovo').id
        reconcile_adv_get_to_pay.onchange_partner_id()
        with self.assertRaises(UserError):
            reconcile_adv_get_to_pay.reconcile_order_done()
        # 预收预付时，本次核销金额不能大于未核销金额
        reconcile_adv_get_to_pay.advance_payment_ids.this_reconcile = 900.0
        with self.assertRaises(UserError):
            reconcile_adv_get_to_pay.reconcile_order_done()
        # 状态为‘done’,再次执行reconcile_order_done(),执行continue
        reconcile_pay_to_pay_done = self.env['reconcile.order'].create({'partner_id': self.env.ref('core.jd').id, 'date': "2016-02-20",
                                                                        'to_partner_id': self.env.ref('core.yixun').id,
                                                                        'business_type': 'pay_to_pay',
                                                                        'name': 'TO20160010',
                                                                        'state': 'done'})
        with self.assertRaises(UserError):
            reconcile_pay_to_pay_done.reconcile_order_done()

    def test_reconcile_order_draft_adv_pay_to_get(self):
        ''' Test: reconcile_order_draft: adv_pay_to_get  '''
        # 预收冲应收
        reconcile = self.env.ref('money.reconcile_adv_pay_to_get')
        reconcile.partner_id = self.env.ref('core.jd').id
        reconcile.onchange_partner_id()
        reconcile.advance_payment_ids.to_reconcile = 300.0
        reconcile.advance_payment_ids.this_reconcile = 300.0
        reconcile.reconcile_order_done()
        reconcile.reconcile_order_draft()

        # 核销单已撤销，不能再次撤销 报错
        with self.assertRaises(UserError):
            reconcile.reconcile_order_draft()

    def test_reconcile_order_draft_adv_get_to_pay(self):
        ''' Test: reconcile_order_draft: adv_get_to_pay '''
        self.env.ref('money.pay_2000').money_order_done()
        # 预付冲应付
        reconcile = self.env.ref('money.reconcile_adv_get_to_pay')
        reconcile.partner_id = self.env.ref('core.lenovo').id
        reconcile.onchange_partner_id()
        reconcile.advance_payment_ids.to_reconcile = 600.0
        reconcile.advance_payment_ids.this_reconcile = 600.0
        reconcile.reconcile_order_done()
        reconcile.reconcile_order_draft()

        # 反核销时，金额不相同 报错
        reconcile.reconcile_order_done()
        with self.assertRaises(UserError):
            reconcile.payable_source_ids.this_reconcile = 666.0
            reconcile.reconcile_order_draft()

    def test_reconcile_order_draft_pay_to_pay(self):
        ''' Test: reconcile_order_draft: pay_to_pay '''
        # 应收转应收
        reconcile = self.env.ref('money.reconcile_pay_to_pay')
        reconcile.partner_id = self.env.ref('core.lenovo').id
        reconcile.onchange_partner_id()
        reconcile.payable_source_ids.to_reconcile = 300.0
        reconcile.payable_source_ids.this_reconcile = 300.0
        reconcile.reconcile_order_done()
        reconcile.reconcile_order_draft()

        # 业务伙伴和转入往来单位不能相同 报错
        reconcile.reconcile_order_done()
        with self.assertRaises(UserError):
            reconcile.to_partner_id = self.env.ref('core.lenovo').id
            reconcile.onchange_partner_id()
            reconcile.reconcile_order_draft()

    def test_onchange_partner_id(self):
        '''核销单onchange_partner_id()'''
        # onchange_partner_id改变partner_id
        self.partner_id = self.env.ref('core.jd').id
        self.env['reconcile.order'].onchange_partner_id()
        self.assertEqual(self.partner_id, self.env.ref('core.jd').id)
        # onchange_partner_id改变为空
        self.partner_id = False
        self.env['reconcile.order'].onchange_partner_id()
        self.assertEqual(self.partner_id, False)
        # 转入转出客户相同，执行if
        reconcile_pay_to_pay_partner_same = self.env['reconcile.order'].create({'partner_id': self.env.ref('core.jd').id,
                                                                                'to_partner_id': self.env.ref('core.jd').id,
                                                                                'business_type': 'pay_to_pay',
                                                                                'name': 'TO20160009', 'date': "2016-02-20",
                                                                                'note': 'ywp pay to pay'})
        with self.assertRaises(UserError):
            reconcile_pay_to_pay_partner_same.reconcile_order_done()

        self.env.ref('money.reconcile_get_to_get').reconcile_order_done()
