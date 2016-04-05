# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm
import time


class TestWarehouseOrder(TransactionCase):
    def setUp(self):
        super(TestWarehouseOrder, self).setUp()

        self.overage_in = self.browse_ref('warehouse.wh_in_whin0')
        self.others_in = self.browse_ref('warehouse.wh_in_whin1')
        self.overage_in_cable = self.browse_ref('warehouse.wh_move_line_14')
        self.others_out = self.browse_ref('warehouse.wh_out_whout0')
        self.internal = self.browse_ref('warehouse.wh_internal_whint0')

        # 其他入库调拨网线48个到总仓
        self.others_in.approve_order()
        # 睡眠2秒，使得下一次入库的确认时间和上次入库不一致
        time.sleep(2)

        # 盘盈入库调拨网线12000个到总仓
        self.overage_in.approve_order()

        # 将120个网线从总仓调拨到上海仓库
        self.internal.approve_order()

        # 将12个网线从上海仓库发往其他仓库
        self.others_out.approve_order()

    def test_approve(self):

        # 此时其他入库单的others_in的剩余数量应该为0
        self.assertEqual(self.others_in.line_in_ids.qty_remaining, 0)
        # 此时盘盈入库单的overage_in的剩余数量应该为12000 - 120 + 48
        self.assertEqual(self.overage_in_cable.qty_remaining, 12000 - 120 + 48)
        # 此时调拨单上的剩余数量应该位120 - 12
        self.assertEqual(self.internal.line_out_ids.qty_remaining, 120 - 12)

        # 所有审核后的单据状态都应该位done
        self.assertEqual(self.overage_in.state, 'done')
        self.assertEqual(self.others_in.state, 'done')
        self.assertEqual(self.others_out.state, 'done')
        self.assertEqual(self.internal.state, 'done')

    def test_unlink(self):

        # 审核后的单据无法被取消
        with self.assertRaises(except_orm):
            self.others_in.unlink()

        # 审核后的单据无法被取消
        with self.assertRaises(except_orm):
            self.overage_in.unlink()

        # 审核后的单据无法被取消
        with self.assertRaises(except_orm):
            self.internal.unlink()

        # 审核后的单据无法被取消
        with self.assertRaises(except_orm):
            self.others_out.unlink()

        self.others_out.cancel_approved_order()
        self.internal.cancel_approved_order()
        self.overage_in.cancel_approved_order()
        self.others_in.cancel_approved_order()

        # 取消后的单据可以被删除
        self.others_in.unlink()
        self.overage_in.unlink()
        self.internal.unlink()
        self.others_out.unlink()

    def test_cancel_approve(self):

        # 存在已经被匹配的出库时入库无法被取消
        with self.assertRaises(except_orm):
            self.others_in.cancel_approved_order()

        # 出库单据审核后剩余数量需要减去出库数量12
        self.assertEqual(self.internal.line_out_ids.qty_remaining, 120 - 12)
        self.others_out.cancel_approved_order()
        # 出库单据反审核后剩余数量会恢复为120
        self.assertEqual(self.internal.line_out_ids.qty_remaining, 120)

        self.assertEqual(self.others_in.line_in_ids.qty_remaining, 0)
        self.assertEqual(self.overage_in_cable.qty_remaining, 12000 - 120 + 48)
        self.internal.cancel_approved_order()
        self.assertEqual(self.others_in.line_in_ids.qty_remaining, 48)
        self.assertEqual(self.overage_in_cable.qty_remaining, 12000)

        self.overage_in.cancel_approved_order()
        self.others_in.cancel_approved_order()

    def test_origin(self):
        self.assertEqual(self.others_in.origin, 'wh.in.others')
        self.assertEqual(self.others_out.origin, 'wh.out.others')
        self.assertEqual(self.internal.origin, 'wh.internal')
        self.assertEqual(self.overage_in.origin, 'wh.in.overage')
