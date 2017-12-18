# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestAutoExchange(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(TestAutoExchange, self).setUp()
        self.bsd = self.env.ref('base.BSD')

    def test_get_exchange(self):
        ''' 测试 自动取汇率 '''
        self.bsd.get_exchange()
