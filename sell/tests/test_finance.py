# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError

class test_month_product_cost(TransactionCase):

    def setUp(self):
        super(test_month_product_cost, self).setUp()
        self.period_id = self.env.ref('finance.period_201601')

    def test_generate_issue_cost(self):
        """本月成本结算 相关逻辑的测试"""
        checkout_wizard_row = self.env['checkout.wizard'].create({'date':'2016-01-31','period_id':self.period_id.id})
        with self.assertRaises(UserError):
            checkout_wizard_row.button_checkout()
        sell_order_rows = self.env['sell.order'].search({})
        [sell_order_row.sell_order_done() for sell_order_row in sell_order_rows]
        sell_delivery_rows = self.env['sell.delivery'].search({})
        [sell_delivery_row.sell_delivery_done() for sell_delivery_row in sell_delivery_rows]
        sell_adjust_rows = self.env['sell.adjust'].search({})
        [sell_adjust_row.sell_adjust_done() for sell_adjust_row in sell_adjust_rows]
        self.env['month.product.cost'].generate_issue_cost(self.period_id)