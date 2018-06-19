# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields


class TestAutoExchange(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(TestAutoExchange, self).setUp()
        self.usd = self.env.ref('base.USD')
        self.exchange_line = self.env.ref('auto_exchange.auto_exchange_line_1')

    def test_get_exchange(self):
        ''' 测试 自动取汇率 '''
        self.usd.get_exchange()

        # 中国银行找不到您的(%s)币别汇率
        bsd = self.env.ref('base.BSD')
        with self.assertRaises(UserError):
            bsd.get_exchange()

        # 取汇率，self 不存在的情况
        self.env['res.currency'].get_exchange()

    def test_compute_current_rate(self):
        ''' Test: _compute_current_rate '''
        self.exchange_line.date = fields.Datetime.now()
        self.assertTrue(self.exchange_line.currency_id.rate == 1.0)


class TestCurrencyMoneyOrder(TransactionCase):
    def test_get_rate_silent(self):
        ''' Test: get_rate_silent '''
        self.usd = self.env.ref('base.USD')
        money_order = self.env.ref('money.get_40000')
        order_line_1 = self.env.ref('money.get_line_1')
        order_line_1.currency_id = self.usd.id
        # 报错：没有设置会计期间内的外币 %s 汇率
        with self.assertRaises(UserError):
            self.env['money.order'].get_rate_silent(money_order.date, order_line_1.currency_id.id)

        self.env.ref('auto_exchange.auto_exchange_line_1').exchange = 0.8
        self.env['money.order'].get_rate_silent(money_order.date, order_line_1.currency_id.id)
