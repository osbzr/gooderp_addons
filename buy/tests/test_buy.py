# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_buy(TransactionCase):
    def test_buy(self):
        ''' 测试采购订单  '''
        order = self.env.ref('buy.buy_order_1')
        
        #采购订单行的已入库数量为0时，将产品状态写为未入库
        new_order = order.copy()
        new_order._get_buy_goods_state()
        #采购订单行的已入库数量小于产品数量时，将产品状态写为部分入库
        for line in new_order.line_ids :
            line.quantity_in = 5
        new_order._get_buy_goods_state()
            
        #产品使用批次管理时，将订单行拆分
        new_order = order.copy()
        for line in new_order.line_ids :
            line.goods_id = 1
            new_order.buy_generate_receipt()
        #订单行新建时，调出仓库的默认值？
            line.create({
                         'order_id':new_order.id,})
        #采购订单行为空时，不能审核
            line.unlink()
        with self.assertRaises(except_orm):
            new_order.buy_order_done()
        
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
