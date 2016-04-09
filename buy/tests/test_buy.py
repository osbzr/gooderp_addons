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
        #采购订单行为空时，不能审核
            line.unlink()
        with self.assertRaises(except_orm):
            new_order.buy_order_done()
        #新建订单行，默认值
        new_order = order.copy()
        line_id = new_order.line_ids.with_context({'warehouse_type':'supplier'}).create({
                                   'order_id':new_order.id,
                                   })
            
        # 审核采购订单
        order.buy_order_done()
        order.buy_order_draft()
        order.buy_order_done()
        
        receipt = self.env['buy.receipt'].search([('order_id','=',order.id)])
        receipt.buy_receipt_done()
        
        # 已经收货不能反审核了
        with self.assertRaises(except_orm):
            order.buy_order_draft()
        
        # 入库单测试(_get_buy_money_state)
        new_order = order.copy()
        new_order.buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',new_order.id)])
        receipt.write({'state':'draft'})
        receipt._get_buy_money_state()
        receipt.buy_receipt_done()
        receipt._get_buy_money_state()
        receipt.write({'payment':receipt.amount - 1})
        receipt._get_buy_money_state()
        receipt.write({'payment':receipt.amount})
        receipt._get_buy_money_state()
        #移库单审核
        bank_account = self.env.ref('core.alipay')
        bank_account.write({'balance':1000000,})
        receipt.write({'state':'draft',
                       'bank_account_id':bank_account.id,
                       'payment':'',})
        with self.assertRaises(except_orm):
            receipt.buy_receipt_done()
        receipt.write({'state':'draft',
                       'bank_account_id':'',
                       'payment':10,})
        with self.assertRaises(except_orm):
            receipt.buy_receipt_done()
        receipt.write({'state':'draft',
                       'bank_account_id':bank_account.id,
                       'payment':receipt.amount + 1,})
        with self.assertRaises(except_orm):
            receipt.buy_receipt_done()
        #采购费用行判断
        receipt.write({'state':'draft',
                       'bank_account_id':'',
                       'payment':'',})
        receipt.cost_line_ids.create({'buy_id':receipt.id,
                          'partner_id':4,
                          'amount':100,})
        receipt.buy_receipt_done()
        #测试生成付款单
        receipt.write({'state':'draft',
                       'bank_account_id':bank_account.id,
                       'payment':receipt.amount,})
        receipt.buy_receipt_done()
        #移库单审核返回True
        new_receipt = receipt.copy()
        new_receipt.write({'state':'draft',
                       'order_id':'',})
        new_receipt.buy_receipt_done()
        with self.assertRaises(except_orm):
            new_receipt.buy_receipt_done()
        
        #退货单测试
        order_return = self.env.ref('buy.buy_order_return_1')
        order_return_copy = order_return.copy()
        return_line = self.env['wh.move.line'].create({
                                          'move_id':order_return_copy.buy_move_id.id,
                                          'goods_id':1,
                                          'warehouse_dest_id':1,
                                          'warehouse_id':2,
                                          'goods_qty':1,
                                          'price':5,
                                          'type':'out',
                                          })
        order_return_copy._get_buy_return_state()
        order_return_copy.buy_receipt_done()
        order_return_copy._get_buy_return_state()
        order_return_copy.write({
                                 'payment':5,
                                 })
        order_return_copy._get_buy_return_state()
        order_return_copy.write({
                                 'payment':5.85,
                                 })
        order_return_copy._get_buy_return_state()
        

    def test_onchange(self):
        ''' 测试onchange '''
        order = self.env.ref('buy.buy_order_1')

        new_order = order.copy()
        new_order.buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',new_order.id)])
        receipt.onchange_discount_rate()
        receipt.write({'discount_rate':10})
        receipt.onchange_discount_rate()
        
        order_return = self.env.ref('buy.buy_order_return_1')
        order_return_copy = order_return.copy()
        return_line = self.env['wh.move.line'].create({
                                          'move_id':order_return_copy.buy_move_id.id,
                                          'warehouse_dest_id':1,
                                          'goods_id':1,
                                          'warehouse_id':2,
                                          'goods_qty':1,
                                          'price':5,
                                          'type':'out',
                                          })
        order_return_copy.onchange_discount_rate()
        
        order.write({'discount_rate':10})
        order.onchange_discount_rate()
        order.line_ids[0].onchange_goods_id()
        order.line_ids[0].write({'discount_rate':10})
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
        order.buy_order_done()
        order.buy_order_draft()
        with self.assertRaises(except_orm):
            order.buy_order_draft()

