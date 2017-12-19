# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestAutoExchange(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(TestAutoExchange, self).setUp()
        self.usd = self.env.ref('base.USD')

    def test_get_exchange(self):
        ''' 测试 自动取汇率 '''
        self.usd.get_exchange()

        # 中国银行找不到您的(%s)币别汇率
        # bsd = self.env.ref('base.BSD')
        # with self.assertRaises(UserError):
        #     bsd.get_exchange()
