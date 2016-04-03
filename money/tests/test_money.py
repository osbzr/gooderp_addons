# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_money(TransactionCase):
    def test_money_order(self):
        ''' 测试收付款  '''
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.pay_2000').money_order_done()
    
    def test_other_money_order(self):
        ''' 测试其他收入支出 '''
        self.env.ref('money.other_get_60').other_money_done()
        #with self.assertRaises(except_orm):
            # 账户余额不足
        #    self.env.ref('money.other_pay_9000').other_money_done()
        # 转出账户收一笔款
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.other_pay_9000').other_money_done()
    
    def test_money_transfer_order(self):
        ''' 测试转账 '''
        with self.assertRaises(except_orm):
            # 转出账户余额不足
            self.env.ref('money.transfer_300').money_transfer_done()
        # 转出账户收一笔款
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.transfer_300').money_transfer_done()
    
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
    
