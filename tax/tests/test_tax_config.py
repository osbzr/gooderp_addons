# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TaxConfigWizard(TransactionCase):
    def test_set_default(self):
        ''' Test: set_default '''
        tax_config_obj = self.env['tax.config.settings']
        tax_config_obj.set_default_goods_supplier()
        tax_config_obj.set_default_service_supplier()
        tax_config_obj.set_default_customer()
        tax_config_obj.set_default_buy_goods_account()
        tax_config_obj.set_default_sell_goods_account()
        tax_config_obj.set_default_tax_num()
        tax_config_obj.set_default_country_name()
        tax_config_obj.set_default_country_tel_number()
        tax_config_obj.set_default_company_name()
        tax_config_obj.set_default_province_password()
        tax_config_obj.set_default_country_password()
        tax_config_obj.set_default_dmpt_name()
        tax_config_obj.set_default_dmpt_password()
