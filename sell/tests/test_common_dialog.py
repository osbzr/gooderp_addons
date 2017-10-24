# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestCommonDialogWizard(TransactionCase):

    def setUp(self):
        '''准备数据'''
        super(TestCommonDialogWizard, self).setUp()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])

    def test_do_confirm(self):
        '''弹窗确认按钮，正常情况'''
        vals = {}
        for line in self.delivery.line_out_ids:
            vals = {
                'type': 'inventory',
                'warehouse_id': self.env.ref('warehouse.warehouse_inventory').id,
                'warehouse_dest_id': self.delivery.warehouse_id.id,
                'line_in_ids': [(0, 0, {
                        'goods_id': line.goods_id.id,
                        'attribute_id': line.attribute_id.id,
                        'uos_id': line.uos_id.id,
                        'goods_qty': line.goods_qty,
                                'uom_id': line.uom_id.id,
                                'cost_unit': line.goods_id.cost
                                }
                )]
            }
        wizard = self.env['common.dialog.wizard'].with_context({
            'active_ids': self.delivery.id,
            'active_model': 'sell.delivery',
            'func': 'goods_inventory',
            'args': [vals],
        }).create({})
        wizard.do_confirm()

    def test_do_confirm_no_func(self):
        '''弹窗确认按钮，不传func时应报错'''
        wizard = self.env['common.dialog.wizard'].with_context({
            'active_ids': self.delivery.id,
            'active_model': 'sell.delivery',
            'func': '',
        }).create({})
        with self.assertRaises(ValueError):
            wizard.do_confirm()

    def test_do_confirm_no_active_ids(self):
        '''弹窗确认按钮，不传active_ids,active_model 时应报错'''
        wizard = self.env['common.dialog.wizard'].with_context({
            'active_ids': False,
            'active_model': '',
            'func': 'goods_inventory',
        }).create({})
        with self.assertRaises(ValueError):
            wizard.do_confirm()
