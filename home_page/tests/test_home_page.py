# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from psycopg2 import IntegrityError
from odoo.exceptions import UserError


class TestHomePage(TransactionCase):
    """
    test_home_page: 因为 改变依赖关系，home_page 不能取到
    """

    def test_home_page(self):
        """测试首页的显示情况"""
        partner_action = self.env.ref('base.action_partner_form')
        partner_credit = self.env.ref('base.field_res_partner_credit_limit')
        self.env['home.page'].create({'sequence': 10, 'action': partner_action.id, 'menu_type': 'all_business',
                                      'domain': '[]', 'context': '{}'})
        self.env['home.page'].create({'sequence': 10, 'action': partner_action.id, 'menu_type': 'amount_summary',
                                      'domain': [], 'context': {}, 'note_one': 'partner', 'compute_field_one': partner_credit.id})
        self.env['home.page'].create({'sequence': 10, 'action': partner_action.id, 'menu_type': 'report',
                                      'domain': [], 'context': {}})
        self.env['home.page'].get_action_url()

    def test_onchange_action(self):
        '''测试 onchange_action
        '''
        partner_action_view = self.env.ref('base.action_partner_form')
        partner_action = self.env['home.page'].create({'sequence': 10, 'action': partner_action_view.id, 'menu_type': 'all_business',
                                                       'domain': '[]', 'context': '{}'})
        result = partner_action.onchange_action()
        real_result = {'domain': {'view_id': [
            ('model', '=', u'res.partner'), ('type', '=', 'tree')]}}
        self.assertTrue(result == real_result)
