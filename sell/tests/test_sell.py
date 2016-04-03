# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_sell(TransactionCase):
    def test_sell(self):
        ''' 测试销售订单  '''
        order = self.env.ref('sell.sell_order_1')
        
        # 审核销售订单
        order.sell_order_done()
        
        receipt = self.env['sell.delivery'].search([('order_id','=',order.id)])
        # receipt.sell_delivery_done()
        
        # 已经发货不能反审核了
        order.sell_order_draft()

    def test_onchange(self):
        ''' 测试onchange '''
        order = self.env.ref('sell.sell_order_1')
        order.onchange_discount_rate()
        order.line_ids[0].onchange_goods_id()
        order.line_ids[0].onchange_discount_rate()
