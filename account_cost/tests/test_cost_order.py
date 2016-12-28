# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class test_cost_order(TransactionCase):
    def setUp(self):
        super(test_cost_order, self).setUp()

        self.cost_order_1 = self.env.ref('account_cost.cost_order_1')
        self.cost_order_1.partner_id = self.env.ref('core.zt')

        self.buy_order_1 = self.env.ref('buy.buy_order_1')
        self.buy_order_1.buy_order_done()
        self.receipt = self.env['buy.receipt'].search([('order_id', '=', self.buy_order_1.id)])

    def test_cost_order_confim(self):
        ''' 测试 服务订单 审核 '''
        # no name
        self.cost_order_1.name = ''
        self.cost_order_1.cost_order_confim()
        # 重复审核
        with self.assertRaises(UserError):
            self.cost_order_1.cost_order_confim()

    def test_cost_order_confim_cancel_then_confirm(self):
        ''' 测试 服务订单 审核终止的订单'''
        self.cost_order_1.state = 'cancel'
        # 不能审核已中止的订单
        with self.assertRaises(UserError):
            self.cost_order_1.cost_order_confim()
    def test_cost_order_confim_no_line(self):
        ''' 测试 服务订单 审核 没有明细行'''
        # no line_ids
        self.cost_order_1.line_ids.unlink()
        with self.assertRaises(UserError):
            self.cost_order_1.cost_order_confim()
    def test_cost_order_confim_has_prepayment_no_bank(self):
        ''' 测试 服务订单 审核 有预付没有结算账户 '''
        # 有预付款，但没有结算账户
        self.cost_order_1.prepayment = 10
        with self.assertRaises(UserError):
            self.cost_order_1.cost_order_confim()
            
    def test_confim_generate_payment_order(self):
        ''' 测试 服务订单 审核 生成付款单 '''
        self.cost_order_1.prepayment = 10
        self.cost_order_1.bank_account_id = self.env.ref('core.alipay')
        self.cost_order_1.cost_order_confim()

    def test_cost_order_draft(self):
        ''' 测试 服务订单 审核 '''
        self.cost_order_1.cost_order_confim()
        self.cost_order_1.cost_order_draft()
        # 重复反审核
        with self.assertRaises(UserError):
            self.cost_order_1.cost_order_draft()
