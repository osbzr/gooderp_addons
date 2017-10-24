# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestLocation(TransactionCase):
    def setUp(self):
        ''' 准备基本数据 '''
        super(TestLocation, self).setUp()
        self.location = self.env.ref('warehouse.a001_location')

    def test_change_location(self):
        ''' 测试商品库位转移 按钮 '''
        self.location.change_location()


class TestChangeLocation(TransactionCase):
    def setUp(self):
        ''' 准备基本数据 '''
        super(TestChangeLocation, self).setUp()

        self.location = self.env.ref('warehouse.a001_location')
        self.others_wh_in = self.env.ref('warehouse.wh_in_whin0')
        self.env.ref(
            'warehouse.wh_move_line_14').location_id = self.location.id
        # 填充库位数量
        self.others_wh_in.approve_order()

        # location: a0001; goods: cable; qty: 12000
        self.assertEqual(self.location.current_qty, 12000)

        self.location_b001 = self.env.ref('warehouse.b001_location')
        self.change_loc = self.env['change.location'].create({
            'from_location': self.location.id,
            'to_location': self.location_b001.id,
            'change_qty': 1,
        })

    def test_confirm_change(self):
        ''' 测试商品库位转移 '''
        self.location_b001.goods_id = self.env.ref('goods.cable').id
        self.change_loc.confirm_change()

        self.assertEqual(self.location.current_qty, 11999)
        self.assertEqual(self.location_b001.current_qty, 1)

        # 报错：请检查转出库位与转入库位的产品、产品属性是否都相同！
        self.location_b001.goods_id = self.env.ref('goods.mouse').id
        with self.assertRaises(UserError):
            self.change_loc.confirm_change()

        # 报错：转出数量不能小于零
        self.change_loc.change_qty = -1
        with self.assertRaises(UserError):
            self.change_loc.confirm_change()

        # 报错：转出库位 与转入库位不能相同
        self.change_loc.change_qty = 1
        self.change_loc.to_location = self.location.id
        with self.assertRaises(UserError):
            self.change_loc.confirm_change()

        # 报错：转出数量不能大于库位现有数量
        self.change_loc.change_qty = 12000
        self.change_loc.to_location = self.location_b001.id
        with self.assertRaises(UserError):
            self.change_loc.confirm_change()

    def test_fields_view_get(self):
        ''' 测试 fields_view_get '''
        self.assertEqual(self.location_b001.current_qty, 0)
        act_id = self.location_b001.id
        # 报错：转出库位产品数量不能小于等于 0
        with self.assertRaises(UserError):
            self.env['change.location'].with_context({'active_model': 'location',
                                                      'active_ids': [act_id]}).fields_view_get(None, 'form', False, False)
