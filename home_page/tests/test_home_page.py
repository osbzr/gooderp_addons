# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase


class test_home_page(TransactionCase):

    def test_home_page(self):
        """测试首页的显示情况"""
        self.env['home.page'].get_action_url()
