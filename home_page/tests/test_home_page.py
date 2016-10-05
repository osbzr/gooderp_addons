# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class test_home_page(TransactionCase):

    def test_home_page(self):
        """测试首页的显示情况"""
        self.env['home.page'].get_action_url()

    def test_onchange_action(self):
    	'''测试 onchange_action '''
    	result = self.env.ref('home_page.top_9').onchange_action()
    	real_result = {'domain': {'view_id': [('model', '=', u'res.partner'), ('type', '=', 'tree')]}}
    	self.assertTrue(result == real_result)
        