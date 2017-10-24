# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestMenu(TransactionCase):
    ''' 测试菜单 '''

    def test_tag(self):
        '''测试菜单'''
        a = self.browse_ref('base.menu_ir_property').load_create_tag()
