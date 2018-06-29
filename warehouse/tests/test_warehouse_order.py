# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
import time


class TestWarehouseOrder(TransactionCase):
    ''' 测试仓库的其他出库单单据和调拨单 '''

    def setUp(self):
        super(TestWarehouseOrder, self).setUp()

        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin1').date = '2016-02-06'
        self.env.ref('warehouse.wh_in_whin3').date = '2016-02-06'
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        self.overage_in = self.browse_ref('warehouse.wh_in_whin0')
        self.overage_in_cable = self.browse_ref('warehouse.wh_move_line_14')

        self.others_in = self.browse_ref('warehouse.wh_in_whin1')
        self.others_in_cable = self.browse_ref('warehouse.wh_move_line_15')
        self.others_in_keyboard_mouse = self.browse_ref(
            'warehouse.wh_move_line_16')

        self.others_in_2 = self.browse_ref('warehouse.wh_in_whin3')
        self.others_in_2_keyboard_mouse = self.browse_ref(
            'warehouse.wh_move_line_keyboard_mouse_in_2')

        self.others_in_keyboard_mouse = self.browse_ref(
            'warehouse.wh_move_line_16')

        self.others_out = self.browse_ref('warehouse.wh_out_whout0')
        self.others_out_2 = self.browse_ref('warehouse.wh_out_whout1')

        self.internal = self.browse_ref('warehouse.wh_internal_whint0')

        # 其他入库调拨网线48个和键鼠套装48个到总仓
        self.others_in.approve_order()
        # 睡眠2秒，使得下一次入库的确认时间和上次入库不一致
        time.sleep(2)

        # 其他入库键鼠套装48个到总仓
        self.others_in_2.approve_order()

        # 盘盈入库调拨网线12000个到总仓
        self.overage_in.approve_order()

        # 将120个网线从总仓调拨到上海仓库
        self.internal.approve_order()

        # 将12个网线从上海仓库发往其他仓库
        self.others_out.approve_order()

        # 将24个键盘套装从总仓发往其他仓库
        self.others_out_2.approve_order()

    def test_approve(self):
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id

        # 此时其他入库单的others_in的剩余数量应该为0
        self.assertEqual(self.others_in_cable.qty_remaining, 0)
        # 此时盘盈入库单的overage_in的剩余数量应该为12000 - 120 + 48
        self.assertEqual(self.overage_in_cable.qty_remaining, 12000 - 120 + 48)
        # 此时调拨单上的剩余数量应该位120 - 12
        self.assertEqual(self.internal.line_out_ids.qty_remaining, 120 - 12)

        # 根据FIFO原则，应该先取先入库的商品，所以先取others_in的前24个键盘套装
        self.assertEqual(self.others_in_keyboard_mouse.qty_remaining, 24)
        self.assertEqual(self.others_in_2_keyboard_mouse.qty_remaining, 48)

        # 所有审核后的单据状态都应该为done
        self.assertEqual(self.overage_in.state, 'done')
        self.assertEqual(self.others_in.state, 'done')
        self.assertEqual(self.others_in_2.state, 'done')
        self.assertEqual(self.others_out.state, 'done')
        self.assertEqual(self.others_out_2.state, 'done')
        self.assertEqual(self.internal.state, 'done')

    def test_approve_create_zero_wh_in(self):
        ''' 测试 create_zero_wh_in '''
        self.others_out.cancel_approved_order()
        self.internal.cancel_approved_order()
        self.env.user.company_id.is_enable_negative_stock = True
        self.env.ref('warehouse.wh_move_line_17').goods_qty = 20000
        self.internal.approve_order()

    def test_unlink(self):

        # 审核后的单据无法被取消
        with self.assertRaises(UserError):
            self.others_in.unlink()

        # 审核后的单据无法被取消
        with self.assertRaises(UserError):
            self.overage_in.unlink()

        # 审核后的单据无法被取消
        with self.assertRaises(UserError):
            self.internal.unlink()

        # 审核后的单据无法被取消
        with self.assertRaises(UserError):
            self.others_out.unlink()

        self.others_out.cancel_approved_order()
        self.others_out_2.cancel_approved_order()
        self.internal.cancel_approved_order()
        self.overage_in.cancel_approved_order()
        self.others_in.cancel_approved_order()

        # 取消后的单据可以被删除
        self.others_in.unlink()
        self.others_out_2.unlink()
        self.overage_in.unlink()
        self.internal.unlink()
        self.others_out.unlink()

        # 删除后的单据应该不存在
        self.assertTrue(not self.others_in.exists())
        self.assertTrue(not self.others_out_2.exists())
        self.assertTrue(not self.overage_in.exists())
        self.assertTrue(not self.internal.exists())
        self.assertTrue(not self.others_out.exists())

    def test_cancel_approve_line_action_draft(self):
        # 存在已经被匹配的出库时入库无法被取消
        with self.assertRaises(UserError):
            self.others_in.cancel_approved_order()

    def test_cancel_approve(self):
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id

        # 取消键盘套装的出库，此时others_in的键盘套装数量回复到48
        self.others_out_2.cancel_approved_order()
        self.assertEqual(self.others_in_keyboard_mouse.qty_remaining, 48)

        # 出库单据审核后剩余数量需要减去出库数量12
        self.assertEqual(self.internal.line_out_ids.qty_remaining, 120 - 12)
        self.others_out.cancel_approved_order()
        # 出库单据反审核后剩余数量会恢复为120
        self.assertEqual(self.internal.line_out_ids.qty_remaining, 120)

        self.assertEqual(self.others_in_cable.qty_remaining, 0)
        self.assertEqual(self.overage_in_cable.qty_remaining, 12000 - 120 + 48)
        self.internal.cancel_approved_order()
        self.assertEqual(self.others_in_cable.qty_remaining, 48)
        self.assertEqual(self.overage_in_cable.qty_remaining, 12000)

        self.overage_in.cancel_approved_order()
        self.others_in.cancel_approved_order()

        # 所有反审核后的单据状态都应该为draft
        self.assertEqual(self.overage_in.state, 'draft')
        self.assertEqual(self.others_in.state, 'draft')
        self.assertEqual(self.others_out.state, 'draft')
        self.assertEqual(self.internal.state, 'draft')

        # 没有明细行的单据不可以被审核通过
        with self.assertRaises(UserError):
            self.internal.line_out_ids.unlink()
            self.internal.approve_order()

        # 测试utils里面对于多重继承的时候报错
        # 在with里面，with接收之后里面的代码会生效，没有回溯
        with self.assertRaises(ValueError):
            self.others_in._inherits = {
                'wh.move': 'move_id',
                'wh.out': 'out_id',
            }
            self.others_in.approve_order()

    def test_origin(self):
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.assertEqual(self.others_in.origin, 'wh.in.others')
        self.assertEqual(self.others_out.origin, 'wh.out.others')
        self.assertEqual(self.internal.origin, 'wh.internal')
        self.assertEqual(self.overage_in.origin, 'wh.in.inventory')

    def test_create(self):
        temp_out = self.env['wh.out'].create({'name': '/', 'type': 'others'})
        temp_in = self.env['wh.in'].create({'name': '/', 'type': 'others'})
        temp_internal = self.env['wh.internal'].create({'name': '/'})

        self.assertNotEqual(temp_out.name, '/')
        self.assertNotEqual(temp_in.name, '/')
        self.assertNotEqual(temp_internal.name, '/')

        self.assertEqual(temp_out.origin, 'wh.out.others')
        self.assertEqual(temp_in.origin, 'wh.in.others')
        self.assertEqual(temp_internal.origin, 'wh.internal')

    def test_get_default_warehouse(self):
        '''获取调出仓库'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        order = self.env['wh.out'].with_context({
            'warehouse_type': 'stock',
        }).create({'type': 'others',
                   'line_out_ids': [(0, 0, {'goods_id': self.browse_ref('goods.mouse').id,
                                            'type': 'out',
                                            })]})
        # 验证明细行上仓库是否是订单上调出仓库
        hd_stock = self.browse_ref('warehouse.hd_stock')
        order.warehouse_id = hd_stock
        line = order.line_out_ids[0]
        self.assertTrue(line.warehouse_id == hd_stock)
        self.env['wh.out'].create({'type': 'others'})

    def test_get_default_warehouse_dest(self):
        '''获取调入仓库'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        order = self.env['wh.in'].with_context({
            'warehouse_dest_type': 'stock'
        }).create({'type': 'others',
                   'line_in_ids': [(0, 0, {'goods_id': self.browse_ref('goods.mouse').id})]})
        # 验证明细行上仓库是否是订单上调入仓库
        hd_stock = self.browse_ref('warehouse.hd_stock')
        order.warehouse_dest_id = hd_stock
        line = order.line_in_ids[0]
        self.assertTrue(line.warehouse_dest_id == hd_stock)
        self.env['wh.in'].create({'type': 'others'})

    def test_onchange_type(self):
        '''当业务类别变化时，调入库位也发生变化'''
        # 其它出库单
        self.others_out.type = 'inventory'
        warehouse_inventory = self.browse_ref('warehouse.warehouse_inventory')
        self.others_out.onchange_type()
        self.assertTrue(self.others_out.warehouse_dest_id ==
                        warehouse_inventory)

        # 其它入库单
        self.others_in_2.type = 'inventory'
        self.others_in_2.onchange_type()
        self.assertTrue(self.others_in_2.warehouse_id == warehouse_inventory)

    def test_create_voucher_init(self):
        '''初始化其他入库单时生成凭证的情况'''
        self.others_in_2.cancel_approved_order()
        self.others_in_2.is_init = True
        self.others_in_2.approve_order()
        self.others_in_2.cancel_approved_order()

    def test_create_voucher_no_voucher_line(self):
        '''确认其他入库单时生成凭证 没有凭证行，删除凭证  的情况'''
        self.others_in_2.cancel_approved_order()
        self.others_in_2_keyboard_mouse.cost = 0.0
        self.others_in_2.approve_order()

        # 键鼠套装入库成本为0再出库时，没有凭证行，删除凭证行
        self.others_out.cancel_approved_order()
        self.internal.cancel_approved_order()
        self.others_out_2.cancel_approved_order()
        self.others_in.cancel_approved_order()  # 为了键鼠套装入库成本为0,匹配到others_in_2
        self.env.ref('warehouse.wh_move_line_out_2').cost = 0.0
        self.others_out_2.approve_order()

    def test_voucher_can_be_draft(self):
        '''其他单据生成的凭证不能反审核'''
        voucher = self.env.ref('finance.voucher_1')
        voucher.ref = 'wh.in,1'
        voucher.voucher_done()
        with self.assertRaises(UserError):
            voucher.voucher_can_be_draft()

    def test_goods_inventory_others_out(self):
        ''' 其他出库单审核商品不足时调用创建盘盈入库方法 '''
        self.others_out.cancel_approved_order()
        for line in self.others_out.line_out_ids:
            vals = {
                'type': 'inventory',
                'warehouse_id': self.env.ref('warehouse.warehouse_inventory').id,
                'warehouse_dest_id': self.others_out.warehouse_id.id,
                'line_in_ids': [(0, 0, {
                        'goods_id': line.goods_id.id,
                        'attribute_id': line.attribute_id.id,
                        'goods_uos_qty': line.goods_uos_qty,
                        'uos_id': line.uos_id.id,
                                'goods_qty': line.goods_qty,
                                'uom_id': line.uom_id.id,
                                'cost_unit': line.goods_id.cost
                                }
                )]
            }
            self.others_out.goods_inventory(vals)

    def test_goods_inventory_internal(self):
        ''' 内部调拨单审核商品不足时调用创建盘盈入库方法 '''
        self.others_out.cancel_approved_order()
        self.internal.cancel_approved_order()
        for line in self.internal.line_out_ids:
            vals = {
                'type': 'inventory',
                'warehouse_id': self.env.ref('warehouse.warehouse_inventory').id,
                'warehouse_dest_id': self.internal.warehouse_id.id,
                'line_in_ids': [(0, 0, {
                        'goods_id': line.goods_id.id,
                        'attribute_id': line.attribute_id.id,
                        'goods_uos_qty': line.goods_uos_qty,
                        'uos_id': line.uos_id.id,
                                'goods_qty': line.goods_qty,
                                'uom_id': line.uom_id.id,
                                'cost_unit': line.goods_id.cost
                                }
                )]
            }
            self.internal.goods_inventory(vals)

    def test_approve_order_twice(self):
        '''重复确认报错'''
        with self.assertRaises(UserError):
            self.others_in.approve_order()
        with self.assertRaises(UserError):
            self.internal.approve_order()
        with self.assertRaises(UserError):
            self.others_out.approve_order()

    def test_cancel_approved_order_twice(self):
        '''重复撤销报错'''
        self.others_in_2.cancel_approved_order()
        with self.assertRaises(UserError):
            self.others_in_2.cancel_approved_order()

        self.others_out.cancel_approved_order()
        with self.assertRaises(UserError):
            self.others_out.cancel_approved_order()

        self.internal.cancel_approved_order()
        with self.assertRaises(UserError):
            self.internal.cancel_approved_order()


class TestCheckOutWizard(TransactionCase):
    # 放在这里测试，因为代码实现时，需要安装 warehouse 模块
    def test_button_checkout_diff_cost(self):
        ''' Test button_checkout：diff_cost '''
        # 期初 keyboard_mouse 产品数量及成本
        self.env.ref('finance.period_201411').is_closed = False
        self.env.ref('warehouse.wh_in_whin1').date = '2014-11-06'
        self.env.ref('warehouse.wh_move_line_16').cost = 600
        self.browse_ref('warehouse.wh_in_whin1').approve_order() # 入库 48

        others_out_1 = self.env.ref('warehouse.wh_out_whout1')
        others_out_1.date = '2014-11-06'
        others_out_1.approve_order() # 出库 24
        self.env.ref('finance.period_201411').is_closed = True

        # 当月入库 keyboard_mouse 产品数量及成本
        self.env.ref('warehouse.wh_in_whin3').date = '2014-12-06'
        self.env.ref('warehouse.wh_move_line_keyboard_mouse_in_2').cost = 400
        self.browse_ref('warehouse.wh_in_whin3').approve_order()
        # 当月出库
        others_out_2 = self.env.ref('warehouse.wh_out_whout1').copy()
        others_out_2.date = '2014-12-06'
        others_out_2.approve_order()
        # 月末结账
        wizard_2 = self.env['checkout.wizard'].create({'date': '20141213'})
        wizard_2.onchange_period_id()
        self.env['month.product.cost'].generate_issue_cost(wizard_2.period_id, wizard_2.date)
        self.env.ref('finance.period_201412').is_closed = True

        # 发出成本算法为 定额成本std
        others_out_3 = self.env.ref('warehouse.wh_out_whout1').copy()
        others_out_3.date = '2015-12-06'
        self.env.ref('goods.keyboard_mouse').cost_method = 'std'
        others_out_3.approve_order()
        # 月末结账
        wizard_3 = self.env['checkout.wizard'].create({'date': '20151213'})
        wizard_3.onchange_period_id()
        self.env['month.product.cost'].generate_issue_cost(wizard_3.period_id, wizard_3.date)
