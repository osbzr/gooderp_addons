# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import datetime


class TestScm(TransactionCase):
    def setUp(self):
        super(TestScm, self).setUp()

        self.stock_request = self.env['stock.request'].create({
            'date': datetime.now(),
        })

        self.goods_mouse = self.env.ref('goods.mouse')  # goods  mouse
        self.goods_keyboard = self.env.ref('goods.keyboard')  # goods  keyboard
        self.goods_cable = self.env.ref('goods.cable')  # goods  cable
        self.goods_keyboard_mouse = self.env.ref(
            'goods.keyboard_mouse')  # goods  keyboard_mouse
        self.goods_computer = self.env.ref('goods.computer')  # goods  computer
        self.goods_iphone = self.env.ref('goods.iphone')  # goods  computer
        self.goods_cable.supplier_id = self.env.ref('core.lenovo')
        self.goods_keyboard_mouse.supplier_id = self.env.ref('core.lenovo')
        self.goods_mouse.supplier_id = self.env.ref('core.lenovo')
        self.goods_keyboard.supplier_id = self.env.ref('core.lenovo')
        self.goods_computer.supplier_id = self.env.ref('core.lenovo')
        self.goods_iphone.supplier_id = self.env.ref('core.lenovo')
        self.goods_keyboard.min_stock_qty = 50

        self.wh_move_in_1 = self.env.ref('warehouse.wh_in_whin0')
        self.wh_move_line_mouse = self.env.ref(
            'warehouse.wh_move_line_12')  # wh.move.line  mouse
        self.wh_move_line_keyboard_1 = self.env.ref(
            'warehouse.wh_move_line_13')  # wh.move.line  keyboard
        self.wh_move_line_keyboard_2 = self.wh_move_line_keyboard_1.copy()
        self.wh_move_in_2 = self.wh_move_in_1.copy()

        self.sell_order_1 = self.env.ref(
            'sell.sell_order_1')  # sell.order  mouse

        self.buy_order = self.env.ref('buy.buy_order_1')  # buy.order  keyboard
        self.buy_order_keyboard_1 = self.env.ref('buy.buy_order_line_1')

        self.wh_bom = self.env.ref('warehouse.wh_bom_0')
        self.wh_bom.type = 'assembly'

    def test_stock_query(self):
        ''' 测试 查询库存 方法'''
        # 计算计算当前数量
        self.wh_move_in_1.approve_order()
        sell_line_keyboard_1 = self.env['sell.order.line'].create({
            'order_id': self.sell_order_1.id,
            'goods_id': self.goods_keyboard.id,
            'attribute_id': self.env.ref('goods.keyboard_white').id
        })
        sell_line_keyboard_1.onchange_goods_id()
        sell_line_keyboard_2 = sell_line_keyboard_1.copy()
        sell_line_keyboard_2.onchange_goods_id()

        self.stock_request.stock_query()

    def test_stock_request_done(self):
        ''' 测试 审核 方法'''
        self.wh_move_in_1.approve_order()

        # 请输入补货申请行商品的供应商 存在
        self.goods_keyboard_mouse.min_stock_qty = 1
        self.env.ref(
            'goods.iphone_black').goods_id = self.goods_keyboard_mouse.id

        self.stock_request.stock_query()

        # 保证不存在多条未审核购货订单行
        self.env.ref('buy.buy_order_line_1_same').attribute_id = False
        self.env.ref('buy.buy_return_order_line_1').order_id.partner_id = self.env.ref(
            'core.zt').id

        self.stock_request.stock_request_done()

    def test_stock_request_done_request_qty_zero(self):
        ''' 测试 request_qty 为 0 '''
        self.wh_move_in_1.approve_order()
        # 请输入补货申请行商品的供应商 存在
        self.goods_keyboard_mouse.min_stock_qty = 100
        self.stock_request.stock_query()
        # 保证不存在多条未审核购货订单行
        self.env.ref('buy.buy_order_line_1_same').attribute_id = False
        self.env.ref('buy.buy_return_order_line_1').order_id.partner_id = self.env.ref(
            'core.zt').id

        for line in self.stock_request.line_ids:
            line.request_qty = 0
        self.stock_request.stock_request_done()

    def test_stock_request_done_no_same_supplier(self):
        ''' 测试 找不到相同供应商的购货订单 '''
        self.stock_request.stock_query()
        # 保证不存在多条未审核购货订单行
        self.env.ref('buy.buy_order_line_1_same').attribute_id = False
        self.env.ref('buy.buy_return_order_1').buy_order_done()

        for request_line in self.stock_request.line_ids:
            request_line.supplier_id = self.env.ref('core.zt').id

        self.stock_request.stock_request_done()

    def test_stock_request_done_raise_multi_line(self):
        ''' 测试 raise 供应商%s 商品%s%s 存在多条未审核购货订单行 '''
        self.wh_move_in_1.approve_order()
        self.buy_order_keyboard_2 = self.buy_order_keyboard_1.copy()

        self.stock_request.stock_query()
        # raise 供应商%s 商品%s%s 存在多条未审核购货订单行
        with self.assertRaises(UserError):
            self.stock_request.stock_request_done()

    def test_stock_request_done_raise_no_supplier(self):
        ''' 测试 raise 请输入补货申请行商品%s%s 的供应商'''
        self.wh_move_in_1.approve_order()
        self.goods_mouse.supplier_id = False

        self.stock_request.stock_query()
        # raise 请输入补货申请行商品%s%s 的供应商
        with self.assertRaises(UserError):
            self.stock_request.stock_request_done()

    def test_stock_request_done_child_has_child(self):
        ''' 测试 审核 方法： 组装单中的子件自身还存在模板'''
        bom_id = self.env['wh.bom'].create({
            'name': 'goods_computer',
            'type': 'assembly'
        })
        self.env['wh.bom.line'].create({
            'bom_id': bom_id.id,
            'goods_id': self.goods_computer.id,
            'goods_qty': 1,
            'type': 'parent'
        })
        self.env['wh.bom.line'].create({
            'bom_id': bom_id.id,
            'goods_id': self.goods_keyboard_mouse.id,
            'goods_qty': 1,
            'type': 'child'
        })
        self.goods_computer.min_stock_qty = 1
        self.stock_request.stock_query()

        # 保证不存在多条未审核购货订单行
        self.env.ref('buy.buy_order_line_1_same').attribute_id = False
        self.env.ref('buy.buy_return_order_line_1').order_id.partner_id = self.env.ref(
            'core.zt').id

        self.stock_request.stock_request_done()

    def test_stock_request_done_twice(self):
        '''不能重复审核'''
        self.wh_move_in_1.approve_order()
        self.stock_request.stock_query()
        # 保证不存在多条未审核购货订单行
        self.env.ref('buy.buy_order_line_1_same').attribute_id = False
        self.env.ref('buy.buy_return_order_line_1').order_id.partner_id = self.env.ref(
            'core.zt').id
        self.stock_request.stock_request_done()
        with self.assertRaises(UserError):
            self.stock_request.stock_request_done()
