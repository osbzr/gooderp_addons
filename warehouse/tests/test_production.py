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

    # def test_approve(self):
    #     # 库存不足的时候直接拆卸，会报没有库存的异常
    #     with self.assertRaises(except_orm):
    #         self.disassembly.approve_order()
    #
    #     # 先组装，后拆卸可以正常出入库
    #     self.assembly.approve_order()
    #     self.disassembly.approve_order()
    #
    #     self.assertEqual(self.assembly.state, 'done')
    #     self.assertEqual(self.disassembly.state, 'done')
    #
    # def test_cancel(self):
    #     self.assembly.approve_order()
    #     self.disassembly.approve_order()
    #
    #     # 组装的产品已经被拆卸过了，此时会报异常
    #     with self.assertRaises(except_orm):
    #         self.assembly.cancel_approved_order()
    #
    #     self.disassembly.cancel_approved_order()
    #     self.assembly.cancel_approved_order()
    #
    #     # 取消后的单据的状态为draft
    #     self.assertEqual(self.assembly.state, 'draft')
    #     self.assertEqual(self.disassembly.state, 'draft')
    #
    # def test_unlink(self):
    #     self.assembly.approve_order()
    #     self.disassembly.approve_order()
    #
    #     # 没法删除已经审核果的单据
    #     with self.assertRaises(except_orm):
    #         self.assembly.unlink()
    #
    #     # 组装的产品已经被拆卸过了，此时会报异常
    #     with self.assertRaises(except_orm):
    #         self.assembly.unlink()
    #
    #     self.disassembly.cancel_approved_order()
    #     self.assembly.cancel_approved_order()
    #
    #     # 反审核后可以被删除掉
    #     self.assembly.unlink()
    #     self.disassembly.unlink()
    #
    #     # 删除后的单据应该不存在
    #     self.assertTrue(not self.disassembly.exists())
    #     self.assertTrue(not self.assembly.exists())
    #
    # def test_create(self):
    #     temp_assembly = self.env['wh.assembly'].create({'name': '/'})
    #     temp_disassembly = self.env['wh.disassembly'].create({'name': '/'})
    #
    #     # 编号应该由ir.sequence指定，不应该等于指定值
    #     self.assertNotEqual(temp_assembly.name, '/')
    #     self.assertNotEqual(temp_disassembly.name, '/')
    #
    #     # 验证origin是否正确
    #     self.assertEqual(temp_assembly.origin, 'wh.assembly')
    #     self.assertEqual(temp_disassembly.origin, 'wh.disassembly')
    #
    # def test_apportion(self):
    #     self.assembly.fee = 0
    #     self.assembly.approve_order()
    #
    #     # demo数据中入库的成本为鼠标 40 * 1，键盘 80 * 2, 所以成本应该位100
    #     self.assertEqual(self.assembly.line_in_ids.price, 100)
    #
    #     self.assembly.cancel_approved_order()
    #     self.assembly.fee = 100
    #     self.assembly.approve_order()
    #
    #     # 指定组装费用位100，此时成本应该位150
    #     self.assertEqual(self.assembly.line_in_ids.price, 150)
    #
    #     self.disassembly.approve_order()
    #
    #     # 170的成本被拆分成鼠标 * 1(成本40) + 键盘 * 1（成本80）,所以此时应该均分为50 + 100
    #     self.assertEqual(self.disassembly_mouse.price, 50)
    #     self.assertEqual(self.disassembly_keyboard.price, 100)
    #
    #     self.disassembly.cancel_approved_order()
    #     self.disassembly.fee = 120
    #
    #     self.disassembly.approve_order()
    #     # 指定拆卸费用位120，此时平分270，此时应该位 90 + 180
    #     self.assertEqual(self.disassembly_mouse.price, 90)
    #     self.assertEqual(self.disassembly_keyboard.price, 180)

    def test_bom(self):
        # 创建一个新的临时bom
        self.assembly.bom_id = self.env['wh.bom'].create({'name': 'temp', 'type': 'assembly'})

        self.assembly.update_bom()
        self._test_assembly_bom(self.assembly, self.assembly.bom_id)

        self.assembly.line_in_ids.unlink()
        self.assembly.line_out_ids.unlink()

        assembly_values = {
            'bom_id': self.assembly.bom_id,
            'line_in_ids': False,
            'line_out_ids': False,
        }
        results = self.assembly.onchange(assembly_values, 'bom_id', {'bom_id': 'true'})
        self._test_assembly_bom_by_results(self.assembly, self.assembly.bom_id, results['value'])

        self.disassembly.update_bom()
        self._test_disassembly_bom(self.disassembly, self.disassembly.bom_id)

        self.disassembly.line_in_ids.unlink()
        self.disassembly.line_out_ids.unlink()

        disassembly_values = {
            'bom_id': self.disassembly.bom_id,
            'line_in_ids': False,
            'line_out_ids': False,
        }
        results = self.disassembly.onchange(disassembly_values, 'bom_id', {'bom_id': 'true'})
        self._test_disassembly_bom_by_results(self.disassembly, self.disassembly.bom_id, results['value'])

    def _test_assembly_bom_by_results(self, assembly, bom, results):
        self._test_bom(assembly, bom, parent_results=results['line_in_ids'], child_results=results['line_out_ids'])

    def _test_disassembly_bom_by_results(self, disassembly, bom, results):
        self._test_bom(disassembly, bom, parent_results=results['line_out_ids'], child_results=results['line_in_ids'])

    def _test_assembly_bom(self, assembly, bom):
        self._test_bom(assembly, bom, parent_attr='line_in_ids', child_attr='line_out_ids')

    def _test_disassembly_bom(self, disassembly, bom):
        self._test_bom(disassembly, bom, parent_attr='line_out_ids', child_attr='line_in_ids')

    def _test_bom(self, assembly, bom, parent_attr='line_in_ids', child_attr='line_out_ids',
                  parent_results=None, child_results=None):
        bom_parent_ids = [(parent.goods_id.id, parent.goods_qty) for parent in bom.line_parent_ids]
        bom_child_ids = [(child.goods_id.id, child.goods_qty) for child in bom.line_child_ids]

        if parent_results and child_results:
            assembly_parent_ids = [(parent[2]['goods_id'], parent[2]['goods_qty']) for parent in parent_results]
            assembly_child_ids = [(child[2]['goods_id'], child[2]['goods_qty']) for child in child_results]
        else:
            assembly_parent_ids = [(parent.goods_id.id, parent.goods_qty) for parent in getattr(assembly, parent_attr)]
            assembly_child_ids = [(child.goods_id.id, child.goods_qty) for child in getattr(assembly, child_attr)]

        self.assertEqual(len(bom_parent_ids), len(assembly_parent_ids))
        self.assertEqual(len(bom_child_ids), len(assembly_child_ids))

        for parent in assembly_parent_ids:
            self.assertTrue(parent in bom_parent_ids)

        for child in assembly_child_ids:
            self.assertTrue(child in bom_child_ids)
