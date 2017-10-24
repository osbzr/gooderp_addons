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
        self.others_in_2 = self.browse_ref('warehouse.wh_in_whin3')
        self.others_in_2_keyboard_mouse = self.browse_ref(
            'warehouse.wh_move_line_keyboard_mouse_in_2')

        self.goods_keyboard_mouse = self.browse_ref('goods.keyboard_mouse')
        self.goods_cable = self.browse_ref('goods.cable')

        # 将网线和键盘套装入库
        self.others_in.approve_order()
        time.sleep(2)
        self.others_in_2.approve_order()

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


class TestResCompany(TransactionCase):

    def test_get_operating_cost_account_id(self):
        ''' 测试默认生产费用科目 '''
        self.env['res.company'].create({
            'name': 'demo company',
            'partner_id': self.env.ref('core.zt').id
        })
