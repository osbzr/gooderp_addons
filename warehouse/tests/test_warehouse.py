# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestWarehouse(TransactionCase):
    def setUp(self):
        super(TestWarehouse, self).setUp()

        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        self.hd_warehouse = self.browse_ref('warehouse.hd_stock')
        self.sh_warehouse = self.browse_ref('warehouse.sh_stock')

        self.internal = self.browse_ref('warehouse.wh_internal_whint0')
        self.overage_in = self.browse_ref('warehouse.wh_in_whin0')
        in_mouse_1 = self.env.ref('warehouse.wh_move_line_12')
        in_mouse_1.cost = in_mouse_1.cost_unit * in_mouse_1.goods_qty
        in_mouse_2 = self.env.ref('warehouse.wh_move_line_mouse_2')
        in_mouse_2.cost = in_mouse_2.cost_unit * in_mouse_2.goods_qty
        in_keyboard = self.env.ref('warehouse.wh_move_line_13')
        in_keyboard.cost = in_keyboard.cost_unit * in_keyboard.goods_qty
        in_cable = self.env.ref('warehouse.wh_move_line_14')
        in_cable.cost = in_cable.cost_unit * in_cable.goods_qty

        # 商品 仓库 数量     成本
        # 鼠标 总仓 2.0     80
        # 键盘 总仓 600.0   48000
        # 网线 总仓 11880.0 950400.0
        # 网线 上海 120.0   9600.0
        self.overage_in.approve_order()
        self.internal.approve_order()

    def test_stock(self):
        hd_real_results = [
            {'goods': u'鼠标', 'cost': 80.0, 'qty': 2.0},
            {'goods': u'键盘', 'cost': 48000.0, 'qty': 600.0},
            {'goods': u'网线', 'cost': 950400.0, 'qty': 11880.0},
        ]

        sh_real_results = [
            {'goods': u'网线', 'cost': 9600.0, 'qty': 120.0},
        ]

        for result in self.hd_warehouse.get_stock_qty():
            self.assertTrue(result in hd_real_results)

        self.assertEqual(self.sh_warehouse.get_stock_qty(), sh_real_results)

    def test_name_search(self):
        # 使用name来搜索总仓
        result = self.env['warehouse'].name_search('总仓')
        real_result = [(self.hd_warehouse.id, '[%s]%s' % (
            self.hd_warehouse.code, self.hd_warehouse.name))]

        self.assertEqual(result, real_result)

        # 使用code来搜索总仓
        result = self.env['warehouse'].name_search('000')
        self.assertEqual(result, real_result)

        with self.assertRaises(UserError):
            self.env['warehouse'].get_warehouse_by_type('error')

        # 临时在warehouse的类型中添加一个error类型的错误，让它跳过类型检测的异常
        # 此时在数据库中找不到该类型的仓库，应该报错
        x = self.env['warehouse'].search([('type', '=', 'inventory')])
        x.unlink()
        with self.assertRaises(UserError):
            self.env['warehouse'].get_warehouse_by_type('inventory')

    def test_scan_barcode(self):
        '''扫码出入库'''
        warehouse = self.env['wh.move']
        barcode = '12345678987'
        # 其它入库单扫码
        model_name = 'wh.in'
        order = self.env.ref('warehouse.wh_in_whin3')
        warehouse.scan_barcode(model_name, barcode, order.id)
        warehouse.scan_barcode(model_name, barcode, order.id)
        # 其他出库单扫码
        model_name = 'wh.out'
        order = self.env.ref('warehouse.wh_out_wh_out_attribute')
        warehouse.scan_barcode(model_name, barcode, order.id)
        warehouse.scan_barcode(model_name, barcode, order.id)

        # 调拔单的扫描条码
        model_name = 'wh.internal'
        order = self.env.ref('warehouse.wh_internal_whint0')
        warehouse.scan_barcode(model_name, barcode, order.id)
        # 能找到 barcode 对应的商品
        self.env.ref('warehouse.wh_move_line_17').goods_id = self.env.ref(
            'goods.iphone').id
        warehouse.scan_barcode(model_name, barcode, order.id)

        # 盘点单的扫描条码
        model_name = 'wh.inventory'
        order = self.env.ref('warehouse.wh_inventory_0')
        warehouse.scan_barcode(model_name, barcode, order.id)
        warehouse.scan_barcode(model_name, barcode, order.id)

        # 商品不存在报错
        barcode = '12342312312'
        with self.assertRaises(UserError):
            warehouse.scan_barcode(model_name, barcode, order.id)

        # 商品的条形码扫码出入库
        barcode = '123456789'
        # 其它入库单扫码
        model_name = 'wh.in'
        order = self.env.ref('warehouse.wh_in_whin3')
        warehouse.scan_barcode(model_name, barcode, order.id)
        warehouse.scan_barcode(model_name, barcode, order.id)
        # 其他出库单扫码
        model_name = 'wh.out'
        order = self.env.ref('warehouse.wh_out_wh_out_attribute')
        warehouse.scan_barcode(model_name, barcode, order.id)
        warehouse.scan_barcode(model_name, barcode, order.id)

    def test_check_goods_qty(self):
        '''指定商品，属性，仓库，的当前剩余数量'''
        res = self.env['wh.move'].check_goods_qty(False, False, self.hd_warehouse)[0]
        self.assertTrue(not res)
