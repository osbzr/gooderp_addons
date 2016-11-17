# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import datetime


class test_crm(TransactionCase):
    def setUp(self):
        super(test_crm, self).setUp()

        self.stock_request = self.env['stock.request'].create({
                                                               'date': datetime.now(),
                                                               })

        self.goods_mouse = self.env.ref('goods.mouse') # goods  mouse
        self.goods_keyboard = self.env.ref('goods.keyboard') # goods  keyboard
        self.goods_cable = self.env.ref('goods.cable') # goods  cable
        self.goods_keyboard_mouse = self.env.ref('goods.keyboard_mouse') # goods  keyboard_mouse

        self.wh_move_mouse = self.env.ref('warehouse.wh_in_whin0')
        self.wh_move_line_mouse = self.env.ref('warehouse.wh_move_line_12') # wh.move.line  mouse

        self.wh_move_line_keyboard = self.env.ref('warehouse.wh_move_line_13') # wh.move.line  keyboard

        self.sell_order_mouse = self.env.ref('sell.sell_order_1') # sell.order  mouse

        self.buy_order_keyboard = self.env.ref('buy.buy_order_1') # buy.order  keyboard

    def test_stock_query(self):
        ''' 测试 查询库存 方法'''
        # 计算计算当前数量
        self.wh_move_mouse.approve_order()
        self.stock_request.stock_query()

    def test_stock_request_done(self):
        ''' 测试 审核 方法'''
        self.wh_move_mouse.approve_order()

        # 请输入补货申请行产品的供应商 存在
        self.goods_mouse.supplier_id = self.env.ref('core.lenovo').id
        self.goods_keyboard.supplier_id = self.env.ref('core.lenovo').id
        self.goods_cable.supplier_id = self.env.ref('core.lenovo').id
        self.goods_keyboard_mouse.supplier_id = self.env.ref('core.lenovo').id
        self.goods_keyboard_mouse.min_stock_qty = 5
        self.stock_request.stock_query()
        self.stock_request.stock_request_done()
        
    def test_stock_request_done_raise_no_supplier(self):
        ''' 测试 raise 请输入补货申请行产品%s%s 的供应商'''

        self.wh_move_mouse.approve_order()
        self.stock_request.stock_query()

        # raise 请输入补货申请行产品%s%s 的供应商
        with self.assertRaises(UserError):
            self.stock_request.stock_request_done()

