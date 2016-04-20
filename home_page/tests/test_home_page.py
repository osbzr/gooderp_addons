# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase


class test_invoice(TransactionCase):

    def setUp(self):
        pass

    def test_home_page(self):
        self.env['financial.home'].get_action_url()
