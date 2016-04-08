# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_buy(TransactionCase):
    def test_buy(self):
        ''' 测试采购订单  '''
        order = self.env.ref('buy.buy_order_1')
        
        # 审核采购订单
        order.buy_order_done()
        order.buy_order_draft()
        order.buy_order_done()
        
        receipt = self.env['buy.receipt'].search([('order_id','=',order.id)])
        receipt.buy_receipt_done()
        
        # 已经收货不能反审核了
        with self.assertRaises(except_orm):
            order.buy_order_draft()

    def test_onchange(self):
        ''' 测试onchange '''
        order = self.env.ref('buy.buy_order_1')
        order.onchange_discount_rate()
        order.line_ids[0].onchange_goods_id()
        order.line_ids[0].onchange_discount_rate()

    def test_buy_done(self):
        ''' 测试审核采购订单  '''
        order = self.env.ref('buy.buy_order_1')

        # 审核采购订单
        order.buy_order_done()
        with self.assertRaises(except_orm):
            order.buy_order_done()

    def test_buy_draft(self):
        ''' 测试反审核采购订单  '''
        order = self.env.ref('buy.buy_order_1')

        # 反审核采购订单
        order.buy_order_draft()
        with self.assertRaises(except_orm):
            order.buy_order_draft()

