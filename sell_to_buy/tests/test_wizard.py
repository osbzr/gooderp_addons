# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSellToBuyWizard(TransactionCase):

    def setUp(self):
        super(TestSellToBuyWizard, self).setUp()
        self.order = self.env.ref('buy.buy_order_1')
        self.sell_order = self.env.ref('sell.sell_order_1')
        self.sell_line_1 = self.env.ref('sell.sell_order_line_1')
        self.sell_line_1.copy()
        self.wizard = self.env['sell.to.buy.wizard'].with_context({'active_id': self.order.id}).create({'sell_line_ids': [(6, 0, [self.sell_order.line_ids.ids])]})


    def test_button_ok(self):
        '''生成按钮，复制销货订单行到购货订单中'''
        self.wizard.button_ok()
        self.assertEqual(len(self.order.line_ids), 3)
        self.assertEqual(self.order.sell_id, self.sell_order)
        for line in self.sell_order.line_ids:
            self.assertTrue(line.is_bought)

    def test_button_ok_select_two_sell_order(self):
        '''一次只能勾选同一张销货订单的行'''
        order_2 = self.env.ref('sell.sell_order_2')
        lines = self.sell_order.line_ids + order_2.line_ids
        self.wizard.write({'sell_line_ids': [(6, 0, [lines.ids])]})
        with self.assertRaises(UserError):
            self.wizard.button_ok()

    def test_button_ok_no_sell_line_ids(self):
        '''销货订单行不能为空'''
        wizard = self.env['sell.to.buy.wizard'].with_context({'active_id': self.order.id}).create({'sell_line_ids': []})
        with self.assertRaises(UserError):
            wizard.button_ok()
