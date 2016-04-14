# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class TestProduction(TransactionCase):
    ''' 测试组装单和拆卸单 '''
    def setUp(self):
        super(TestProduction, self).setUp()

        self.assembly = self.browse_ref('warehouse.wh_assembly_ass0')
        self.assembly_mutli = self.browse_ref('warehouse.wh_assembly_ass1')

        self.assembly_mutli_keyboard_mouse_1 = self.browse_ref('warehouse.wh_move_line_ass2')
        self.assembly_mutli_keyboard_mouse_2 = self.browse_ref('warehouse.wh_move_line_ass3')

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
        self.assembly_mutli.fee = 0
        self.assembly_mutli.approve_order()

        # demo数据中成本为鼠标 40 * 2，键盘 80 * 2，所以成本应该为平摊为120
        self.assertEqual(self.assembly_mutli_keyboard_mouse_1.cost_unit, 120)
        self.assertEqual(self.assembly_mutli_keyboard_mouse_2.cost_unit, 120)

        self.assembly_mutli.cancel_approved_order()
        self.assembly_mutli.fee = 100
        self.assembly_mutli.approve_order()

        # 此时组装费用为100，成本增加了100，所以平摊成本增加50
        self.assertEqual(self.assembly_mutli_keyboard_mouse_1.cost_unit, 170)
        self.assertEqual(self.assembly_mutli_keyboard_mouse_2.cost_unit, 170)

        # 取消掉当前的单据，防止其他单据的库存不足
        self.assembly_mutli.cancel_approved_order()

        self.assembly.fee = 0
        self.assembly.approve_order()

        # demo数据中入库的成本为鼠标 40 * 1，键盘 80 * 2, 所以成本应该为100
        self.assertEqual(self.assembly.line_in_ids.cost_unit, 100)

        self.assembly.cancel_approved_order()
        self.assembly.fee = 100
        self.assembly.approve_order()

        # 指定组装费用位100，此时成本应该位150
        self.assertEqual(self.assembly.line_in_ids.cost_unit, 150)

        self.disassembly.approve_order()

        # 170的成本被拆分成鼠标 * 1(成本40) + 键盘 * 1（成本80）,所以此时应该均分为50 + 100
        self.assertEqual(self.disassembly_mouse.cost_unit, 50)
        self.assertEqual(self.disassembly_keyboard.cost_unit, 100)

        self.disassembly.cancel_approved_order()
        self.disassembly.fee = 120

        self.disassembly.approve_order()
        # 指定拆卸费用位120，此时平分270，此时应该位 90 + 180
        self.assertEqual(self.disassembly_mouse.cost_unit, 90)
        self.assertEqual(self.disassembly_keyboard.cost_unit, 180)

    def test_wizard_bom(self):
        self.assembly.bom_id = False
        action = self.assembly.update_bom()

        temp_action = {
            'type': 'ir.actions.act_window',
            'res_model': 'save.bom.memory',
            'view_mode': 'form',
            'target': 'new',
        }

        # 当bom_id不存在的时候，此时保存bom，会自动返回一个wizard
        self.assertEqual(action, temp_action)
        save_bom_memory = self.env['save.bom.memory'].with_context({
            'active_model': self.assembly._name,
            'active_ids': self.assembly.id
        }).create({'name': 'temp'})

        save_bom_memory.save_bom()
        self._test_assembly_bom(self.assembly, self.assembly.bom_id)

        self.disassembly.bom_id = False
        action = self.disassembly.update_bom()

        # 当bom_id不存在的时候，此时保存bom，会自动返回一个wizard
        self.assertEqual(action, temp_action)
        save_bom_memory = self.env['save.bom.memory'].with_context({
            'active_model': self.disassembly._name,
            'active_ids': self.disassembly.id
        }).create({'name': 'temp'})

        save_bom_memory.save_bom()

        self._test_disassembly_bom(self.disassembly, self.disassembly.bom_id)

    def test_bom(self):
        # 创建一个新的临时bom
        self.assembly.bom_id = self.env['wh.bom'].create({'name': 'temp', 'type': 'assembly'})

        # 将当前的组装单保存的临时bom上去
        self.assembly.update_bom()
        # 测试bom和组装单是否一致
        self._test_assembly_bom(self.assembly, self.assembly.bom_id)

        # 删除掉明细行，防止onchange之后明细行上存在历史的数据(缓存)
        self.assembly.line_in_ids.unlink()
        # 当有一个明细行没有值的时候，此时无法通过明细行检测
        with self.assertRaises(except_orm):
            self.assembly.check_parent_length()

        self.assembly.line_out_ids.unlink()

        assembly_values = {
            'bom_id': self.assembly.bom_id,
            'line_in_ids': False,
            'line_out_ids': False,
        }
        # 使用onchange来触发bom的改变，由于相关的bug，只能使用这种方案
        results = self.assembly.onchange(assembly_values, 'bom_id', {'bom_id': 'true'})
        # 测试使用bom后，明细行上和bom的是否一致
        self._test_assembly_bom_by_results(self.assembly, self.assembly.bom_id, results['value'])

        self.disassembly.update_bom()
        self._test_disassembly_bom(self.disassembly, self.disassembly.bom_id)

        self.disassembly.line_in_ids.unlink()
        # 当有一个明细行没有值的时候，此时无法通过明细行检测
        with self.assertRaises(except_orm):
            self.disassembly.check_parent_length()

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
