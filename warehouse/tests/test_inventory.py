# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestInventory(TransactionCase):
    def setUp(self):
        super(TestInventory, self).setUp()

        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin1').date = '2016-02-06'
        self.env.ref('warehouse.wh_in_whin3').date = '2016-02-06'

        self.others_in = self.browse_ref('warehouse.wh_in_whin1')
        self.others_in_2 = self.browse_ref('warehouse.wh_in_whin3')

        self.goods_mouse = self.browse_ref('goods.mouse')
        self.sh_warehouse = self.browse_ref('warehouse.sh_stock')

        # 创建一个临时的一个库存调拨，将1个商品调拨到上海仓库
        self.temp_mouse_in = self.env['wh.move.line'].with_context({
            'type': 'in',
        }).create({
            'move_id': self.others_in.move_id.id,
            'goods_id': self.goods_mouse.id,
            'uom_id': self.goods_mouse.uom_id.id,
            'uos_id': self.goods_mouse.uos_id.id,
            'warehouse_dest_id': self.sh_warehouse.id,
            'goods_qty': 1,
            'goods_uos_qty': self.goods_mouse.anti_conversion_unit(1),
            'cost_unit': 30,
            'lot': 'MOUSE0001',
        })

        # 商品     实际数量 实际辅助数量
        # 键鼠套装  96     2
        # 鼠标     1      1
        # 网线     48     1
        self.others_in.approve_order()
        self.others_in_2.approve_order()
        self.temp_mouse_in.action_done()
        # 创建一个临时的库存调拨，此时数量为0，但是辅助数量为1
        self.temp_mouse_in_zero_qty = self.env['wh.move.line'].with_context({
            'type': 'in',
        }).create({
            'move_id': self.others_in.move_id.id,
            'goods_id': self.goods_mouse.id,
            'uom_id': self.goods_mouse.uom_id.id,
            'uos_id': self.goods_mouse.uos_id.id,
            'warehouse_dest_id': self.sh_warehouse.id,
            'goods_qty': 0,
            'goods_uos_qty': 0,
            'cost_unit': 30,
            'lot': 'MOUSE0002',
        })

        self.temp_mouse_in_zero_qty.action_done()

        self.inventory = self.env['wh.inventory'].create({
            'warehouse_id': self.browse_ref('warehouse.hd_stock').id,
        })
        self.inventory.query_inventory()

    def test_query_inventory(self):
        # 盘点单查询的结果必须和每个商品单据查询的结果一致
        for line in self.inventory.line_ids:
            goods_stock = line.goods_id.get_stock_qty()[0]
            self.assertEqual(goods_stock.get('warehouse'),
                             line.warehouse_id.name)
            if line.goods_id.name == u'网线':  # 网线在途移库 120个，盘点时应减去
                self.assertEqual(goods_stock.get('qty') - 120, line.real_qty)
            else:
                self.assertEqual(goods_stock.get('qty'), line.real_qty)

        # 当指定仓库的时候，选择的行必须是该仓库的
        self.inventory.warehouse_id = self.sh_warehouse
        self.inventory.query_inventory()
        for line in self.inventory.line_ids:
            self.assertEqual(line.warehouse_id, self.sh_warehouse)

        # 指定商品的时候，选择的行必须是该商品的
        self.inventory.goods = [4, self.goods_mouse.id]  # u'鼠标'
        self.inventory.query_inventory()
        for line in self.inventory.line_ids:
            self.assertEqual(line.goods_id.name, u'鼠标')

        self.inventory.unlink()
        self.assertTrue(not self.inventory.exists())

    def test_query_inventory_transfer_order(self):
        '''盘点单查询的盘点数量不应该包含移库在途的,在途移库数量恰好等于仓库中数量'''
        internal_order = self.env.ref('warehouse.wh_internal_whint0')
        for line in internal_order.line_out_ids:
            line.goods_qty = 48
        inventory = self.env['wh.inventory'].create({
            'warehouse_id': self.browse_ref('warehouse.hd_stock').id,
            'goods': u'网线',
        })
        inventory.query_inventory()

    def test_generate_inventory(self):
        for line in self.inventory.line_ids:
            if line.goods_id.name == u'键鼠套装':
                keyboard_mouse = line
            elif line.goods_id.name == u'鼠标':
                mouse = line
            else:
                cable = line

        # 不输入任何值的时候的onchange_qty会讲lot_type设置为nothing
        mouse.onchange_qty()
        self.assertEqual(mouse.lot_type, 'nothing')

        # 实际数量小与系统库存一个的时候，差异数量为-1
        mouse.inventory_qty = mouse.real_qty - 1
        mouse.onchange_qty()
        self.assertEqual(mouse.difference_qty, -1)
        self.assertEqual(mouse.lot_type, 'out')

        # 实际数量大与系统库存一个的时候，差异数量为1
        mouse.inventory_qty = mouse.real_qty + 1
        mouse.onchange_qty()
        self.assertEqual(mouse.difference_qty, 1)
        self.assertEqual(mouse.lot_type, 'in')

        # 对于强制为1的商品，只能添加或减少一个商品
        warning = {'warning': {
            'title': u'警告',
            'message': u'商品上设置了序号为1，此时一次只能盘亏或盘盈一个商品数量',
        }}
        mouse.inventory_qty = mouse.real_qty + 2
        self.assertEqual(mouse.onchange_qty(), warning)

        # 实际辅助数量改变的时候，实际数量应该跟着改变
        mouse.inventory_uos_qty = mouse.real_uos_qty + 1
        mouse.onchange_uos_qty()
        self.assertEqual(mouse.goods_id.conversion_unit(
            mouse.inventory_uos_qty), mouse.inventory_qty)

        mouse.line_role_back()
        mouse.inventory_qty = mouse.real_qty + 1
        mouse.onchange_qty()
        cable.inventory_qty = cable.real_qty - 1
        cable.onchange_qty()

        # 此时鼠标数量+1，网线数量-1，生成一个鼠标的入库单，和网线的出库单
        self.inventory.generate_inventory()
        self.assertTrue(self.inventory.out_id)
        self.assertTrue(self.inventory.in_id)

        # 验证商品
        self.assertEqual(
            self.inventory.out_id.line_out_ids.goods_id, cable.goods_id)
        self.assertEqual(
            self.inventory.in_id.line_in_ids.goods_id, mouse.goods_id)

        # 验证数量
        self.assertEqual(self.inventory.out_id.line_out_ids.goods_qty, 1)
        self.assertEqual(self.inventory.in_id.line_in_ids.goods_qty, 1)

        # 重新盘点的时候相关的出入库单的单据必须未审核
        self.inventory.in_id.approve_order()
        with self.assertRaises(UserError):
            self.inventory.requery_inventory()

        self.inventory.in_id.cancel_approved_order()
        self.inventory.requery_inventory()

        self.inventory.generate_inventory()
        self.inventory.out_id.approve_order()
        self.inventory.in_id.approve_order()

        # 相关的出入库单据完成后，盘点单应该自动完成
        self.assertEqual(self.inventory.state, 'done')

        # 完成的单据不应该被删除
        with self.assertRaises(UserError):
            self.inventory.unlink()

        results = self.inventory.open_in()
        real_results = {
            'type': 'ir.actions.act_window',
            'res_model': 'wh.in',
            'view_mode': 'form',
            'res_id': self.inventory.in_id.id,
        }

        self.assertEqual(results, real_results)

        results = self.inventory.open_out()
        real_results = {
            'type': 'ir.actions.act_window',
            'res_model': 'wh.out',
            'view_mode': 'form',
            'res_id': self.inventory.out_id.id,
        }

        self.assertEqual(results, real_results)

    def test_check_done(self):
        '''盘盈盘亏产生的入库单和出库单审核时检查'''
        self.inventory.query_inventory()
        self.inventory.generate_inventory()

    def test_inventory_get_default_warehouse(self):
        ''' 测试 获取盘点仓库 '''
        self.env['wh.inventory'].create({
            'date': '2016-12-30',
            'goods': '鼠标',
        })
