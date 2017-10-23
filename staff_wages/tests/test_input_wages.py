# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestInputWages(TransactionCase):

    def setUp(self):
        """引入员工工资准备数据"""
        super(TestInputWages, self).setUp()
        self.order = self.env['staff.wages'].create({
            'date': '2017-01-30',
            'payment': self.env.ref('core.alipay').id,
        })
        self.wizard = self.env['create.wages.line.wizard'].with_context({
            'active_id': self.order.id}).create({
            })

    def test_input_change_wages(self):
        """引入员工工资，自动创建员工工资行"""
        self.wizard.input_change_wages()
        self.assertTrue(self.order.line_ids)

    def test_input_change_wages_abnormal_case(self):
        """不传active_id：不创建员工工资行"""
        wizard = self.env['create.wages.line.wizard'].create({})
        wizard.input_change_wages()
        self.assertTrue(not self.order.line_ids)
