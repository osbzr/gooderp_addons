# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
import datetime


class TestNonActiveReport(TransactionCase):
    def setUp(self):
        ''' 呆滞料报表 测试 '''
        super(TestNonActiveReport, self).setUp()

        self.non_active_report_wizard = self.env['non.active.report.wizard'].create({
            'warehouse_id': self.browse_ref('warehouse.hd_stock').id,
            'first_stage_day': 1,
            'second_stage_day': 2,
            'third_stage_day': 3
        })
        self.keyboard_mouse_in_line = self.browse_ref(
            'warehouse.wh_move_line_keyboard_mouse_in_2')
        self.wh_move_line_13 = self.browse_ref('warehouse.wh_move_line_13')
        self.wh_move_line_14 = self.browse_ref('warehouse.wh_move_line_14')
        self.goods_keyboard_mouse = self.browse_ref('goods.keyboard_mouse').id
        self.goods_keyboard = self.browse_ref('goods.keyboard').id
        self.goods_cable = self.browse_ref('goods.cable').id

    def test_open_non_active_report_warehouse(self):
        ''' 呆滞料报表 确定按钮 带warehouse_id 测试 '''
        self.keyboard_mouse_in_line.date = datetime.datetime.now() - \
            datetime.timedelta(days=1)
        self.keyboard_mouse_in_line.state = 'done'
        self.wh_move_line_13.date = datetime.datetime.now() - datetime.timedelta(days=2)
        self.wh_move_line_13.state = 'done'
        self.wh_move_line_14.date = datetime.datetime.now() - datetime.timedelta(days=3)
        self.wh_move_line_14.state = 'done'

        self.non_active_report_wizard.open_non_active_report()

        fir_non_active_report = self.env['non.active.report'].search(
            [('goods_id', '=', self.goods_keyboard_mouse)])
        self.assertEqual(len(fir_non_active_report), 1)
        sec_non_active_report = self.env['non.active.report'].search(
            [('goods_id', '=', self.goods_keyboard)])
        self.assertEqual(len(sec_non_active_report), 1)
        total_non_active_report = self.env['non.active.report'].search([])
        self.assertEqual(len(total_non_active_report), 3)

    def test_open_non_active_report_no_warehouse(self):
        ''' 呆滞料报表 确定按钮 不带warehouse_id 测试 '''
        self.keyboard_mouse_in_line.date = datetime.datetime.now() - \
            datetime.timedelta(days=1)
        self.keyboard_mouse_in_line.state = 'done'

        self.non_active_report_wizard.warehouse_id = False
        self.non_active_report_wizard.open_non_active_report()

    def test_open_non_active_report_update_last_move_line(self):
        ''' 呆滞料报表:更新最后发货日期和最后发货数量 '''
        # 修改调入仓为客户仓库来模拟发货明细行
        self.keyboard_mouse_in_line.warehouse_id = self.env.ref('warehouse.hd_stock')
        self.keyboard_mouse_in_line.warehouse_dest_id = self.env.ref('warehouse.warehouse_customer')
        self.keyboard_mouse_in_line.date = datetime.datetime.now() - \
            datetime.timedelta(days=2)
        self.keyboard_mouse_in_line.state = 'done'

        new_line = self.keyboard_mouse_in_line.copy()
        new_line.date = datetime.datetime.now() - \
                                           datetime.timedelta(days=1)
        new_line.state = 'done'

        self.non_active_report_wizard.open_non_active_report()

    def test_non_active_report_fields_view_get(self):
        ''' 呆滞料报表 fields_view_get 测试 '''
        self.env['non.active.report'].with_context({
            'first_stage_day': 1,
            'second_stage_day_qty': 2,
            'third_stage_day': 3,
            'four_stage_day_qty': 4
        }).fields_view_get(None, 'form', False, False)
