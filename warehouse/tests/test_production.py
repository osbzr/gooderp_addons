# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class TestProduction(TransactionCase):
    def setUp(self):
        super(TestProduction, self).setUp()

        self.assembly = self.browse_ref('warehouse.wh_assembly_ass0')
        self.disassembly = self.browse_ref('warehouse.wh_disassembly_dis1')
        self.disassembly_bom = self.browse_ref('warehouse.wh_bom_0')

        self.disassembly_mouse = self.browse_ref('warehouse.wh_move_line_8')
        self.disassembly_keyboard = self.browse_ref('warehouse.wh_move_line_9')

        self.overage_in = self.browse_ref('warehouse.wh_in_whin0')
        self.overage_in.approve_order()

    def test_approve(self):
        # 库存不足的时候直接拆卸，会报没有库存的异常
        with self.assertRaises(except_orm):
            self.disassembly.approve_order()

        # 先组装，后拆卸可以正常出入库
        self.assembly.approve_order()
        self.disassembly.approve_order()

        self.assertEqual(self.assembly.state, 'done')
        self.assertEqual(self.disassembly.state, 'done')

    def test_cancel(self):
        self.assembly.approve_order()
        self.disassembly.approve_order()

        # 组装的产品已经被拆卸过了，此时会报异常
        with self.assertRaises(except_orm):
            self.assembly.cancel_approved_order()

        self.disassembly.cancel_approved_order()
        self.assembly.cancel_approved_order()

        # 取消后的单据的状态为draft
        self.assertEqual(self.assembly.state, 'draft')
        self.assertEqual(self.disassembly.state, 'draft')

    def test_unlink(self):
        self.assembly.approve_order()
        self.disassembly.approve_order()

        # 没法删除已经审核果的单据
        with self.assertRaises(except_orm):
            self.assembly.unlink()

        # 组装的产品已经被拆卸过了，此时会报异常
        with self.assertRaises(except_orm):
            self.assembly.unlink()

        self.disassembly.cancel_approved_order()
        self.assembly.cancel_approved_order()

        # 反审核后可以被删除掉
        self.assembly.unlink()
        self.disassembly.unlink()

        # 删除后的单据应该不存在
        self.assertTrue(not self.disassembly.exists())
        self.assertTrue(not self.assembly.exists())

    def test_create(self):
        temp_assembly = self.env['wh.assembly'].create({'name': '/'})
        temp_disassembly = self.env['wh.disassembly'].create({'name': '/'})

        # 编号应该由ir.sequence指定，不应该等于指定值
        self.assertNotEqual(temp_assembly.name, '/')
        self.assertNotEqual(temp_disassembly.name, '/')

        # 验证origin是否正确
        self.assertEqual(temp_assembly.origin, 'wh.assembly')
        self.assertEqual(temp_disassembly.origin, 'wh.disassembly')

    def test_apportion(self):
        self.assembly.fee = 0
        self.assembly.approve_order()

        # demo数据中入库的成本为鼠标 80 * 2，键盘 80 * 2, 所以成本应该位120
        self.assertEqual(self.assembly.line_in_ids.price, 120)

        self.assembly.cancel_approved_order()
        self.assembly.fee = 100
        self.assembly.approve_order()

        # 指定组装费用位100，此时成本应该位170
        self.assertEqual(self.assembly.line_in_ids.price, 170)

        self.disassembly.approve_order()

        # 170的成本被拆分成鼠标 * 1(成本80) + 键盘 * 1（成本80）,所以此时应该均分为85
        self.assertEqual(self.disassembly_mouse.price, 85)
        self.assertEqual(self.disassembly_keyboard.price, 85)

        self.disassembly.cancel_approved_order()
        self.disassembly.fee = 100

        self.disassembly.approve_order()
        # 指定拆卸费用位100，此时平方270，此时应该位135
        self.assertEqual(self.disassembly_mouse.price, 135)
        self.assertEqual(self.disassembly_keyboard.price, 135)
