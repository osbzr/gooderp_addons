# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestPayment(TransactionCase):

    def setUp(self):
        super(TestPayment, self).setUp()
        self.order = self.env.ref('buy.buy_order_1')

        # 因同一个业务伙伴不能存在两张未审核的收付款单，把系统里已有的相关业务伙伴未审核的收付款单审核
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.pay_2000').money_order_done()

    def test_request_payment(self):
        '''付款申请'''
        line = self.order.pay_ids.create({
            'name': u'申请付款', 'amount_money': 10, 'buy_id': self.order.id
        })
        line.request_payment()
