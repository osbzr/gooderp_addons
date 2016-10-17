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
        self.env['month.product.cost'].generate_issue_cost(self.period_id)