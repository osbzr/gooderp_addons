# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tools import misc
from odoo.exceptions import UserError


class TestTaxInvoiceOut(TransactionCase):

    def setUp(self):
        super(TestTaxInvoiceOut, self).setUp()
        self.env['ir.values'].set_default('tax.config.settings', 'default_customer', self.env.ref('tax.domestic_customer').id)
        self.sell_invoice = self.env.ref('tax_invoice_out.sell_invoice')

        excel = open(misc.file_open('tax_invoice_out/tests/sell.xlsx').name, 'rb').read().encode('base64')
        wizard = self.env['create.sale.invoice.wizard'].with_context({
            'active_model': 'tax.invoice.out',
            'active_id': self.sell_invoice.id}).create({'excel': excel})
        wizard.create_sale_invoice()

    def test_button_excel(self):
        '''引入excel'''
        wizard_dict = self.sell_invoice.button_excel()
        self.assertTrue(wizard_dict['res_model'], 'create.sale.invoice.wizard')

    def test_invoice_to_sell(self):
        '''反推订单'''
        self.sell_invoice.invoice_to_sell()
        invoice = self.env['cn.account.invoice'].search([('name', '=', '18150335')])
        self.assertTrue(invoice.sell_id.partner_id.name == invoice.partner_name_out)

    def test_tax_invoice_done(self):
        '''确认销售发票'''
        self.sell_invoice.invoice_to_sell()
        self.sell_invoice.tax_invoice_done()
        self.assertTrue(self.sell_invoice.state == 'done')
        # 重复确认报错
        with self.assertRaises(UserError):
            self.sell_invoice.tax_invoice_done()

    def test_tax_invoice_done_error(self):
        '''确认销售发票'''
        with self.assertRaises(UserError):
            self.sell_invoice.tax_invoice_done()

    def test_tax_invoice_draft(self):
        '''反确认销售发票'''
        self.sell_invoice.invoice_to_sell()
        self.sell_invoice.tax_invoice_done()
        self.sell_invoice.tax_invoice_draft()
        self.assertTrue(self.sell_invoice.state == 'draft')
        # 重复反确认报错
        with self.assertRaises(UserError):
            self.sell_invoice.tax_invoice_draft()


class Test_create_sale_invoice_wizard(TransactionCase):

    def setUp(self):
        super(Test_create_sale_invoice_wizard, self).setUp()
        self.sell_invoice = self.env.ref('tax_invoice_out.sell_invoice')

    def test_create_sale_invoice(self):
        '''通过Excel文件导入信息到tax.invoice'''
        excel = open(misc.file_open('tax_invoice_out/tests/sell.xlsx').name, 'rb').read().encode('base64')
        wizard = self.env['create.sale.invoice.wizard'].with_context({
            'active_model': 'tax.invoice.out',
            'active_id': self.sell_invoice.id}).create({'excel': excel})
        wizard.create_sale_invoice()

        # 不传 active_id
        wizard2 = self.env['create.sale.invoice.wizard'].with_context({
            'active_model': 'tax.invoice.out',
            }).create({'excel': excel})
        wizard2.create_sale_invoice()
