# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class TestMoveLine(TransactionCase):
    ''' 测试库存调拨 '''
    def setUp(self):
        super(TestMoveLine, self).setUp()

        self.keyboard_mouse_in_line = self.browse_ref('warehouse.wh_move_line_keyboard_mouse_in_2')
        self.keyboard_mouse_out_line = self.browse_ref('warehouse.wh_move_line_keyboard_mouse_in_2')

        self.mouse_in_line = self.browse_ref('warehouse.wh_move_line_12')
        self.mouse_out_line = self.browse_ref('warehouse.wh_move_line_0')

        self.cable_int_line = self.browse_ref('warehouse.wh_move_line_17')

        self.bj_warehouse = self.browse_ref('warehouse.bj_stock')
        self.hd_warehouse = self.browse_ref('warehouse.hd_stock')

        self.goods_mouse = self.browse_ref('goods.mouse')
        self.goods_cable = self.browse_ref('goods.cable')

    def test_origin_explain(self):
        explain = self.mouse_in_line.get_origin_explain()
        self.assertEqual(explain, u'盘盈')

        explain = self.mouse_out_line.get_origin_explain()
        self.assertEqual(explain, u'组装单子件')

        explain = self.cable_int_line.get_origin_explain()
        self.assertEqual(explain, u'调拨入库')

        self.cable_int_line.move_id.origin = ''
        explain = self.cable_int_line.get_origin_explain()
        self.assertEqual(explain, '')

    def test_default(self):
        # 需找默认的仓库
        self.assertEqual(self.env['wh.move.line']._get_default_warehouse(), False)
        others_warehouse = self.env['wh.move.line'].with_context({
            'warehouse_type': 'others'
        })._get_default_warehouse()

        self.assertEqual(others_warehouse.type, 'others')

        self.assertEqual(self.env['wh.move.line']._get_default_warehouse_dest(), False)
        customer_warehouse = self.env['wh.move.line'].with_context({
            'warehouse_dest_type': 'customer'
        })._get_default_warehouse_dest()

        self.assertEqual(customer_warehouse.type, 'customer')

        defaults = self.env['wh.move.line'].with_context({
            'goods_id': 1,
            'warehouse_id': 1,
        }).default_get(['goods_id', 'warehouse_id'])

        self.assertEqual(defaults.get('goods_id'), 1)
        self.assertEqual(defaults.get('warehouse_id'), 1)

    def test_name_get(self):
        line = self.mouse_in_line
        name = line.name_get()
        real_name = '%s-%s->%s(%s, %s%s)' % (line.move_id.name, line.warehouse_id.name,
                                             line.warehouse_dest_id.name, line.goods_id.name,
                                             str(line.goods_qty), line.uom_id.name)
        self.assertEqual(name[0][1], real_name)

        lot_name = line.with_context({'lot': True}).name_get()
        real_lot_name = '%s-%s-%s' % (line.lot, line.warehouse_dest_id.name, line.qty_remaining)
        self.assertEqual(lot_name[0][1], real_lot_name)

    def test_copy_data(self):
        # 复制的时候，如果该明细行是出库行为，那么需要重新计算成本
        results = self.mouse_out_line.copy_data()
        _, cost_unit = self.mouse_out_line.goods_id.get_suggested_cost_by_warehouse(
            self.mouse_out_line.warehouse_id, self.mouse_out_line.goods_qty)

        self.assertEqual(results.get('cost_unit'), cost_unit)

        _, cost_unit = self.mouse_out_line.goods_id.get_suggested_cost_by_warehouse(
            self.mouse_out_line.warehouse_id, self.mouse_out_line.goods_qty,
            lot_id=self.mouse_out_line.lot_id)

        self.assertEqual(cost_unit, self.mouse_out_line.lot_id.cost_unit)


    def test_get_matching_records_by_lot(self):
        # 批次号未审核的时候获取批次信息会报错
        with self.assertRaises(except_orm):
            self.mouse_out_line.goods_id.get_matching_records_by_lot(
                self.mouse_out_line.lot_id, self.mouse_out_line.goods_qty)

        # 批次号不存在的时候应该报错
        with self.assertRaises(except_orm):
            self.mouse_out_line.goods_id.get_matching_records_by_lot(False, 0)

        self.mouse_out_line.lot_id.action_done()

        results, _ = self.mouse_out_line.goods_id.get_matching_records_by_lot(
            self.mouse_out_line.lot_id, self.mouse_out_line.goods_qty,
            self.mouse_out_line.goods_uos_qty)

        real_results = {
            'line_in_id': self.mouse_out_line.lot_id.id,
            'qty': self.mouse_out_line.goods_qty,
            'uos_qty': self.mouse_out_line.goods_uos_qty,
        }
        self.assertEqual(results[0], real_results)

        # 当前明细行的产品数量大于批次的数量的时候，会报错
        with self.assertRaises(except_orm):
            self.mouse_out_line.goods_id.get_matching_records_by_lot(
                self.mouse_out_line.lot_id,
                self.mouse_out_line.lot_id.qty_remaining + 10)

    def test_attribute(self):
        attribute_in = self.browse_ref('warehouse.wh_in_wh_in_attribute')

        white_iphone = self.browse_ref('warehouse.wh_move_line_iphone_in_1')
        black_iphone = self.browse_ref('warehouse.wh_move_line_iphone_in_2')

        out_iphone = self.browse_ref('warehouse.wh_move_line_iphone_out')

        attribute_in.approve_order()

        # 指定属性的时候，出库成本会寻找和自己属性一致的入库行
        out_iphone.attribute_id = white_iphone.attribute_id
        out_iphone.action_done()
        self.assertEqual(out_iphone.cost_unit, white_iphone.cost_unit)

        out_iphone.action_cancel()
        out_iphone.attribute_id = black_iphone.attribute_id

        real_domain = [
            ('goods_id', '=', out_iphone.goods_id.id),
            ('state', '=', 'done'),
            ('lot', '!=', False),
            ('qty_remaining', '>', 0),
            ('warehouse_dest_id', '=', out_iphone.warehouse_id.id),
            ('attribute_id', '=', black_iphone.attribute_id.id)
        ]

        domain = out_iphone.onchange_attribute_id().get('domain')

        self.assertEqual(real_domain, domain.get('lot_id'))
        out_iphone.action_done()
        self.assertEqual(out_iphone.cost_unit, black_iphone.cost_unit)

    def test_onchange(self):
        results = self.mouse_in_line.onchange_goods_id()
        real_domain = [
            ('goods_id', '=', self.mouse_in_line.goods_id.id),
            ('state', '=', 'done'),
            ('lot', '!=', False),
            ('qty_remaining', '>', 0),
            ('warehouse_dest_id', '=', self.mouse_in_line.warehouse_id.id)
        ]

        # 产品改变的时候，此时仓库存在，lot_id字段的domain值需要包含仓库相关
        self.assertEqual(results['domain']['lot_id'], real_domain)
        self.assertEqual(self.mouse_in_line.goods_qty, 1)

        results = self.keyboard_mouse_out_line.with_context({
            'type': 'out',
        }).onchange_goods_id()

        self.assertEqual(self.keyboard_mouse_out_line.goods_qty,
                         self.keyboard_mouse_out_line.goods_id.conversion_unit(
                             self.keyboard_mouse_out_line.goods_uos_qty))

        # 改变仓库的时候，如果批号的仓库和它不一致，那么批号需要被删除
        self.assertTrue(self.mouse_out_line.lot_id)
        self.mouse_out_line.warehouse_id = self.bj_warehouse
        self.mouse_out_line.onchange_warehouse_id()
        self.assertTrue(not self.mouse_out_line.lot_id)

        # 改变产品的时候，如果批号的产品和它不一致，那么批号也要被删除
        self.mouse_out_line.lot_id = self.mouse_in_line
        self.mouse_out_line.warehouse_id = self.hd_warehouse
        self.mouse_out_line.goods_id = self.goods_cable
        self.mouse_out_line.compute_lot_compatible()
        self.assertTrue(not self.mouse_out_line.lot_id)

        self.mouse_out_line.goods_id = self.goods_mouse

        self.keyboard_mouse_in_line.cost_unit = 0
        results = self.keyboard_mouse_out_line.with_context({
            'type': 'out',
        }).onchange_goods_qty()

        # 出库的单据，数量改变的时候，成本应该跟着改变
        _, cost_unit = self.keyboard_mouse_out_line.goods_id.get_suggested_cost_by_warehouse(
            self.keyboard_mouse_out_line.warehouse_id, self.keyboard_mouse_out_line.goods_qty)
        self.assertEqual(self.keyboard_mouse_out_line.cost_unit, cost_unit)

        self.keyboard_mouse_out_line.goods_uos_qty = 10
        temp_goods_qty = self.keyboard_mouse_out_line.goods_id.conversion_unit(10)
        self.keyboard_mouse_out_line.onchange_goods_uos_qty()
        self.assertEqual(self.keyboard_mouse_out_line.goods_qty, temp_goods_qty)

        self.mouse_in_line.action_done()
        self.mouse_out_line.lot_qty = 0
        self.mouse_out_line.lot_id = self.mouse_in_line
        self.mouse_out_line.with_context({'type': 'internal'}).onchange_lot_id()
        # 当传递type为internal的上下文值的时候，此时lot会设置为lot_id的lot
        self.assertEqual(self.mouse_out_line.lot, self.mouse_out_line.lot_id.lot)
        self.assertEqual(self.mouse_out_line.lot_qty, self.mouse_out_line.lot_id.qty_remaining)

        self.mouse_in_line.discount_rate = 0
        self.mouse_in_line.onchange_discount_rate()
        self.assertEqual(self.mouse_in_line.discount_amount, 0)

        self.mouse_in_line.price = 100
        self.mouse_in_line.discount_rate = 100
        self.mouse_in_line.onchange_discount_rate()
        self.assertEqual(self.mouse_in_line.discount_amount,
                         self.mouse_in_line.goods_qty * self.mouse_in_line.price)

        with self.assertRaises(except_orm):
            self.mouse_in_line.unlink()

        self.mouse_in_line.warehouse_id = self.mouse_in_line.warehouse_dest_id
        with self.assertRaises(except_orm):
            self.mouse_in_line.check_availability()
