# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_money(TransactionCase):
    def test_money_order(self):
        ''' 测试收付款  '''
        last_balance = self.env.ref('core.comm').balance
        # 余额不足不能付款
        with self.assertRaises(except_orm):
            self.env.ref('money.pay_2000').money_order_done()
        # 先收款后付款
        self.env.ref('money.get_40000').money_order_done()
        self.assertEqual(self.env.ref('core.comm').balance,
                          last_balance + 40000)
        self.env.ref('money.pay_2000').money_order_done()
        self.assertEqual(self.env.ref('core.comm').balance,
                          last_balance + 38000)
        # 审核后不能删除
        with self.assertRaises(except_orm):
            self.env.ref('money.get_40000').unlink()
        # 余额不足不能反审核
        with self.assertRaises(except_orm):
            self.env.ref('money.get_40000').money_order_draft()
        # 反审核
        self.env.ref('money.pay_2000').money_order_draft()
        self.env.ref('money.pay_2000').unlink()
        # onchange_date
        self.env.ref('money.get_40000').onchange_date()
        # onchange_partner_id
        self.env.ref('money.get_40000').onchange_partner_id()
        # 当为收款退款时，执行账户余额减少
        self.env.ref('money.get_200_1').money_order_done()
        self.env.ref('money.get_200_1').money_order_draft()
        # 执行money_order_draft 遍历source_ids的操作
        invoice = self.env['money.invoice'].create({'partner_id': self.env.ref('core.jd').id,
                                                'name': 'invoice/2016001',
                                                'category_id':self.env.ref('money.core_category_sale').id,
                                                'amount': 200.0,
                                                'reconciled': 0,
                                                'to_reconcile': 200.0,
                                                'date_due': '2016-09-07'})
        money = self.env['money.order'].create({'partner_id': self.env.ref('core.jd').id,
                                                'name': 'GET/2016001',
                                                'note': 'zxy note',
                                                'line_ids': [(0, 0, {'bank_id':self.env.ref('core.comm').id,
                                                                     'amount': 200.0, 'note': 'money note'})],
                                                'source_ids': [(0, 0, {'name': invoice.id,
                                                                       'category_id':self.env.ref('money.core_category_sale').id,
                                                                       'date': '2016-04-07',
                                                                       'amount': 200.0,
                                                                       'reconciled': 0,
                                                                       'to_reconcile': 200.0,
                                                                       'this_reconcile': 200.0,
                                                                       'date_due': '2016-09-07'})],
                                                'type': 'get'})
        
        money.money_order_done()
        money.money_order_draft()

    def test_other_money_order(self):
        ''' 测试其他收入支出 '''
        self.env.ref('money.other_get_60').other_money_done()
        #with self.assertRaises(except_orm):
            # 账户余额不足
        #    self.env.ref('money.other_pay_9000').other_money_done()
        # 转出账户收一笔款
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.other_pay_9000').other_money_done()
        # 审核状态不可删除
        with self.assertRaises(except_orm):
            self.env.ref('money.other_pay_9000').unlink()
        # 反审核
        self.env.ref('money.other_pay_9000').other_money_draft()
        self.env.ref('money.other_get_60').other_money_draft()
        # 未审核可以删除
        self.env.ref('money.other_pay_9000').unlink()
        # onchange_date  同时执行create时的type=other_get
        invoice = self.env['money.invoice'].create({'name':'invoice',
                                                    'partner_id': self.env.ref('core.jd').id,
                                                    'category_id':self.env.ref('money.core_category_sale').id,
                                                    'amount': 10.0,
                                                    'reconciled': 0})
        other = self.env['other.money.order'].with_context({'type': 'other_get'}).create({'partner_id': self.env.ref('core.jd').id,
                                                    'bank_id': self.env.ref('core.comm').id,
                                                    'line_ids':[(0, 0, {'source_id': invoice.id,
                                                                        'category_id': self.env.ref('money.core_category_sale').id,
                                                                        'amount': 10.0})]})
        other.onchange_date()
        # 执行other_money_done中存在source_id的情况
        with self.assertRaises(except_orm): # 执行amount大于源单的未核销金额时的if
            other.other_money_done()
        # 执行amount不大于源单的未核销金额
        invoice.to_reconcile = 10.0
        other.other_money_done()
        other.other_money_draft()
        # onchange_partner
        self.env.ref('money.other_get_60').onchange_partner()
        # 测试其他收支单金额<0,执行if报错
        other = self.env['other.money.order'].create({
                                                'partner_id': self.env.ref('core.jd').id,
                                                'bank_id': self.env.ref('core.comm').id,
                                                'type': 'other_get'})
        self.env['other.money.order.line'].create({
                                                'other_money_id': other.id,
                                                'category_id': self.env.ref('money.core_category_sale').id,
                                                'amount': -10.0})
        with self.assertRaises(except_orm):
            other.other_money_done()

    def test_money_transfer_order(self):
        ''' 测试转账 '''
        with self.assertRaises(except_orm):
            # 转出账户余额不足
            self.env.ref('money.transfer_300').money_transfer_done()
        # 转出账户收一笔款
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.transfer_300').money_transfer_done()
        with self.assertRaises(except_orm):
            self.env.ref('money.transfer_300').unlink()
        self.env.ref('money.transfer_300').money_transfer_draft()
        self.env.ref('money.transfer_300').unlink()
    
    def test_partner(self):
        ''' 客户对账单 和  银行帐'''
        self.env.ref('core.jd').partner_statements()
        self.env.ref('core.comm').bank_statements()
    
    def test_go_live_order(self):
        self.env['go.live.order'].create({
                    'bank_id':self.env.ref('core.comm').id,
                    'balance':20.0,
                                          })
        self.env['go.live.order'].create({
                    'partner_id':self.env.ref('core.jd').id,
                    'receivable':100.0,
                                          })
        self.env['go.live.order'].create({
                    'partner_id':self.env.ref('core.lenovo').id,
                    'payable':200.0,
                                          })
    
