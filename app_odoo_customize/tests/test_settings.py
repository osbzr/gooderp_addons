# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSettings(TransactionCase):
    def setUp(self):
        super(TestSettings, self).setUp()

    def test_create(self):
        setting = self.env['app.theme.config.settings'].create({
            'app_system_name': 'GoodERP',
        })
        setting.set_default_all()

