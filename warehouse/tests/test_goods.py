# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
import time


class TestGoods(TransactionCase):
    ''' 测试和仓库相关的商品的有关逻辑 '''

    def setUp(self):
        super(TestGoods, self).setUp()
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin1').date = '2016-02-06'
        self.env.ref('warehouse.wh_in_whin3').date = '2016-02-06'
        # 总部仓库
        self.hd_warehouse = self.browse_ref('warehouse.hd_stock')
        self.others_in = self.browse_ref('warehouse.wh_in_whin1')
        self.others_in_cable = self.browse_ref('warehouse.wh_move_line_15')
        self.others_in_keyboard_mouse = self.browse_ref(
            'warehouse.wh_move_line_16')
        self.others_in_cable.cost = self.others_in_cable.cost_unit * self.others_in_cable.goods_qty
        self.others_in_keyboard_mouse.cost = self.others_in_keyboard_mouse.cost_unit * self.others_in_keyboard_mouse.goods_qty
        self.others_in_2 = self.browse_ref('warehouse.wh_in_whin3')
        self.others_in_2_keyboard_mouse = self.browse_ref(
            'warehouse.wh_move_line_keyboard_mouse_in_2')
        self.others_in_2_keyboard_mouse.cost = self.others_in_2_keyboard_mouse.cost_unit * self.others_in_2_keyboard_mouse.goods_qty
        self.goods_keyboard_mouse = self.browse_ref('goods.keyboard_mouse')
        self.goods_cable = self.browse_ref('goods.cable')
        self.goods_iphone = self.browse_ref('goods.iphone')

        # 将网线和键盘套装入库
        self.others_in.approve_order()
        time.sleep(2)
        self.others_in_2.approve_order()
        # 有属性商品iphone黑色和白色入库
        self.others_in_attr = self.browse_ref('warehouse.wh_in_wh_in_attribute')
        self.others_in_attr.approve_order()

    def test_stock(self):
        keyboard_mouse_results = self.goods_keyboard_mouse.get_stock_qty()
        cable_results = self.goods_cable.get_stock_qty()

        real_keyboard_mouse_results = {
            'warehouse': u'总仓',
            'cost': self.others_in_keyboard_mouse.cost + self.others_in_2_keyboard_mouse.cost,
            'qty': self.others_in_keyboard_mouse.goods_qty + self.others_in_2_keyboard_mouse.goods_qty,
        }

        real_cable_results = {
            'warehouse': u'总仓',
            'qty': self.others_in_cable.goods_qty,
            'cost': self.others_in_cable.cost,
        }

        self.assertEqual(real_keyboard_mouse_results,
                         keyboard_mouse_results[0])
        self.assertEqual(real_cable_results, cable_results[0])

    def test_cost(self):
        # 使用_get_cost来获取最后一次历史成本
        cost = self.goods_cable._get_cost(self.hd_warehouse)

        # 应该等于最后一次入库的成本
        self.assertEqual(cost, self.others_in_cable.cost_unit)

        # 忽略掉最后一次入库的行为，此时成本应该去商品的默认成本
        cost = self.goods_cable._get_cost(
            self.hd_warehouse, ignore=self.others_in_cable.id)
        self.assertEqual(cost, self.goods_cable.cost)

        # 使用_get_cost来获取最后一次历史成本
        cost = self.goods_keyboard_mouse._get_cost(self.hd_warehouse)
        self.assertEqual(cost, self.others_in_2_keyboard_mouse.cost_unit)

        # 忽略掉最后一次入库的成本，所以等于上一次入库的成本
        cost = self.goods_keyboard_mouse._get_cost(
            self.hd_warehouse, ignore=self.others_in_2_keyboard_mouse.id)
        self.assertEqual(cost, self.others_in_keyboard_mouse.cost_unit)

        # 使用FIFO来获取成本的函数
        # 48 * 120的键盘套装先入库，48 * 80的键盘套装后入库
        suggested_cost_func = self.goods_keyboard_mouse.get_suggested_cost_by_warehouse

        suggested_cost, _ = suggested_cost_func(self.hd_warehouse, 96)
        self.assertEqual(suggested_cost, 48 * 120 + 48 * 80)

        suggested_cost, _ = suggested_cost_func(self.hd_warehouse, 72)
        self.assertEqual(suggested_cost, 48 * 120 + 24 * 80)

        suggested_cost, _ = suggested_cost_func(self.hd_warehouse, 48)
        self.assertEqual(suggested_cost, 48 * 120)

        suggested_cost, _ = suggested_cost_func(self.hd_warehouse, 24)
        self.assertEqual(suggested_cost, 24 * 120)

        # 忽略掉第一次48 * 120入库的行为，所以获取到的单位成本永远是80
        suggested_cost, _ = suggested_cost_func(
            self.hd_warehouse, 96, ignore_move=self.others_in_keyboard_mouse.id)
        self.assertEqual(suggested_cost, 96 * 80)

        suggested_cost, _ = suggested_cost_func(
            self.hd_warehouse, 72, ignore_move=self.others_in_keyboard_mouse.id)
        self.assertEqual(suggested_cost, 72 * 80)

        suggested_cost, _ = suggested_cost_func(
            self.hd_warehouse, 48, ignore_move=self.others_in_keyboard_mouse.id)
        self.assertEqual(suggested_cost, 48 * 80)

        suggested_cost, _ = suggested_cost_func(
            self.hd_warehouse, 24, ignore_move=self.others_in_keyboard_mouse.id)
        self.assertEqual(suggested_cost, 24 * 80)

    def test_get_matching_records_with_attribute(self):
        '''获取匹配记录（缺货向导确认时）'''
        # 有属性商品获取匹配记录 12 * 4888 的iphone 白、12 * 5000 的iphone 黑入库
        others_in = self.others_in.copy()
        line = self.env['wh.move.line'].create({
            'move_id': others_in.move_id.id,
            'goods_id': self.goods_iphone.id,
            'attribute_id': self.env.ref('goods.iphone_white').id,
            'goods_qty': 1,
            'uom_id': self.goods_iphone.uom_id.id,
            'type': 'in',
            'state': 'done'})
        suggested_cost, _ = self.goods_iphone.with_context({
            'wh_in_line_ids': [line.id]}).get_suggested_cost_by_warehouse(
            self.hd_warehouse, qty=13, attribute=self.env.ref('goods.iphone_white'))

    def test_compute_stock_qty(self):
        self.assertEqual(self.goods_cable.current_qty, 48)

    def test_write(self):
        """商品有库存，不允许修改单位或转化率"""
        with self.assertRaises(UserError):
            self.goods_cable.uos_id = self.env.ref('core.uom_pc').id
        with self.assertRaises(UserError):
            self.goods_cable.conversion = 3

    def test_get_matching_records_has_location(self):
        '''获取匹配记录（出库单行填写了库位）'''
        # 已有键鼠套装入库到总仓的a库位
        wh_out = self.env.ref('warehouse.wh_out_whout1')
        wh_out.line_out_ids[0].location_id = self.env.ref('warehouse.a001_location')
        wh_out.approve_order()


class TestResCompany(TransactionCase):

    def test_get_operating_cost_account_id(self):
        ''' 测试默认生产费用科目 '''
        self.env['res.company'].create({
            'name': 'demo company',
            'partner_id': self.env.ref('core.zt').id
        })
