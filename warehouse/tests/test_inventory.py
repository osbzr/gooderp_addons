# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class TestInventory(TransactionCase):
    def setUp(self):
        super(TestInventory, self).setUp()

        self.others_in = self.browse_ref('warehouse.wh_in_whin1')
        self.others_in_2 = self.browse_ref('warehouse.wh_in_whin3')

        self.goods_mouse = self.browse_ref('goods.mouse')
        self.sh_warehouse = self.browse_ref('warehouse.sh_stock')

        # 创建一个临时的一个库存调拨，将1个产品调拨到上海仓库
        self.temp_mouse_in = self.env['wh.move.line'].with_context({
            'warehouse_type': 'others',
            'type': 'in',
        }).create({
            'goods_id': self.goods_mouse.id,
            'uom_id': self.goods_mouse.uom_id.id,
            'uos_id': self.goods_mouse.uos_id.id,
            'warehouse_dest_id': self.sh_warehouse.id,
            'goods_qty': 1,
            'goods_uos_qty': self.goods_mouse.anti_conversion_unit(1),
            'cost_unit': 30,
            'lot': 'MOUSE0001',
        })

        # 创建一个临时的库存调拨，此时数量为0，但是辅助数量为1
        self.temp_mouse_in_zero_qty = self.env['wh.move.line'].with_context({
            'warehouse_type': 'others',
            'type': 'in',
        }).create({
            'goods_id': self.goods_mouse.id,
            'uom_id': self.goods_mouse.uom_id.id,
            'uos_id': self.goods_mouse.uos_id.id,
            'warehouse_dest_id': self.sh_warehouse.id,
            'goods_qty': 0,
            'goods_uos_qty': 1,
            'cost_unit': 30,
            'lot': 'MOUSE0002',
        })

        # 产品     实际数量 实际辅助数量
        # 键鼠套装  96     2
        # 鼠标     1      1
        # 网线     48     1
        self.others_in.approve_order()
        self.others_in_2.approve_order()
        self.temp_mouse_in.action_done()
        self.temp_mouse_in_zero_qty.action_done()

        self.inventory = self.env['wh.inventory'].create({})
        self.inventory.query_inventory()

    def test_query_inventory(self):
        # 盘点单查询的结果必须和每个产品单据查询的结果一致
        for line in self.inventory.line_ids:
            goods_stock = line.goods_id.get_stock_qty()[0]
            self.assertEqual(goods_stock.get('warehouse'), line.warehouse_id.name)
            self.assertEqual(goods_stock.get('qty'), line.real_qty)

        # 当辅助数量不为0勾选后，会选择到temp_mouse_in_zero_qty相关的库存调拨，此时会出现为一行
        self.assertEqual(len(self.inventory.line_ids), 3)
        self.inventory.uos_not_zero = True
        self.inventory.query_inventory()
        self.assertEqual(len(self.inventory.line_ids), 4)

        # 当指定仓库的时候，选择的行必须是该仓库的
        self.inventory.uos_not_zero = False
        self.inventory.warehouse_id = self.sh_warehouse
        self.inventory.query_inventory()
        for line in self.inventory.line_ids:
            self.assertEqual(line.warehouse_id, self.sh_warehouse)

        # 指定产品的时候，选择的行必须是该产品的
        self.inventory.goods = u'鼠标'
        self.inventory.query_inventory()
        for line in self.inventory.line_ids:
            self.assertEqual(line.goods_id.name, u'鼠标')

        self.inventory.unlink()
        self.assertTrue(not self.inventory.exists())

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

        # 对于强制为1的产品，只能添加或减少一个产品
        warning = {'warning': {
            'title': u'警告',
            'message': u'产品上设置了序号为1，此时一次只能盘亏或盘盈一个产品数量',
        }}
        mouse.inventory_qty = mouse.real_qty + 2
        self.assertEqual(mouse.onchange_qty(), warning)

        # 盘盈盘亏数量和辅助单位数量的盈亏方向应该一致
        warning = {'warning': {
            'title': u'错误',
            'message': u'盘盈盘亏数量应该与辅助单位的盘盈盘亏数量盈亏方向一致',
        }}
        mouse.inventory_qty = mouse.real_qty - 1
        mouse.inventory_uos_qty = mouse.real_uos_qty + 1
        self.assertEqual(mouse.onchange_qty(), warning)

        # 实际辅助数量改变的时候，实际数量应该跟着改变
        mouse.inventory_uos_qty = mouse.real_uos_qty + 1
        mouse.onchange_uos_qty()
        self.assertEqual(mouse.goods_id.conversion_unit(mouse.inventory_uos_qty), mouse.inventory_qty)

        # 盘盈盘亏数量与辅助单位的盘盈盘亏数量盈亏方向不一致的时候，此时没法生成盘盈盘亏单据
        mouse.difference_qty = -1
        mouse.difference_uos_qty = 1
        with self.assertRaises(except_orm):
            self.inventory.generate_inventory()

        mouse.line_role_back()
        mouse.inventory_qty = mouse.real_qty + 1
        mouse.onchange_qty()
        cable.inventory_qty = cable.real_qty - 1
        cable.onchange_qty()

        # 此时鼠标数量+1，网线数量-1，生成一个鼠标的入库单，和网线的出库单
        self.inventory.generate_inventory()
        self.assertTrue(self.inventory.out_id)
        self.assertTrue(self.inventory.in_id)

        # 验证产品
        self.assertEqual(self.inventory.out_id.line_out_ids.goods_id, cable.goods_id)
        self.assertEqual(self.inventory.in_id.line_in_ids.goods_id, mouse.goods_id)

        # 验证数量
        self.assertEqual(self.inventory.out_id.line_out_ids.goods_qty, 1)
        self.assertEqual(self.inventory.in_id.line_in_ids.goods_qty, 1)

        # 重新盘点的时候相关的出入库单的单据必须未审核
        self.inventory.in_id.approve_order()
        with self.assertRaises(except_orm):
            self.inventory.requery_inventory()

        self.inventory.in_id.cancel_approved_order()
        self.inventory.requery_inventory()

        self.inventory.generate_inventory()
        self.inventory.out_id.approve_order()
        self.inventory.in_id.approve_order()

        # 相关的出入库单据完成后，盘点单应该自动完成
        self.assertEqual(self.inventory.state, 'done')

        # 完成的单据不应该被删除
        with self.assertRaises(except_orm):
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
