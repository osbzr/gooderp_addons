# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tools import misc
from odoo.exceptions import UserError


class tax_invoice_in(TransactionCase):
    def setUp(self):
        super(tax_invoice_in, self).setUp()
        self.period_201605 = self.env.ref('finance.period_201605')
        self.tax_invoice_in = self.env['tax.invoice.in'].create({
            'name': self.period_201605.id
        })
        in_file = open(misc.file_open('tax_invoice_in/tests/201805_3.xls').name, 'rb').read().encode('base64')
        self.invoice_wizard = self.env['create.cn.account.invoice.wizard'].create({
            'excel': in_file,
        })

    def test_create_cn_account_invoice(self):
        ''' Test: create account invoice '''
        # context no active_id
        self.invoice_wizard.create_cn_account_invoice()
        # active_id not right
        # self.invoice_wizard.with_context({'active_id': 666}).create_cn_account_invoice()

        # right
        self.invoice_wizard.with_context({'active_id': self.tax_invoice_in.id}).create_cn_account_invoice()

    def test_button_excel(self):
        ''' Test: button_excel '''
        self.tax_invoice_in.button_excel()

    def test_invoice_to_buy(self):
        ''' Test: invoice_to_buy '''
        self.invoice_wizard.with_context({'active_id': self.tax_invoice_in.id}).create_cn_account_invoice()
        # 请设置默认产品供应商 报错
        with self.assertRaises(UserError):
            self.tax_invoice_in.invoice_to_buy()

        # 设置默认产品供应商
        self.env['ir.values'].set_default('tax.config.settings', 'default_goods_supplier',
                                          self.env.ref('core.supplier_category_1').id)
        self.tax_invoice_in.invoice_to_buy()

        # test: _compute_tax_amount
        for line in self.tax_invoice_in.line_ids:
            line.is_deductible = True
            break

    def test_write(self):
        ''' Test: Write '''
        self.tax_invoice_in.name = self.env.ref('finance.period_201604').id

    def test_tax_invoice_done(self):
        ''' Test: tax_invoice_done '''
        self.invoice_wizard.with_context({'active_id': self.tax_invoice_in.id}).create_cn_account_invoice()
        # 设置默认产品供应商
        self.env['ir.values'].set_default('tax.config.settings', 'default_goods_supplier',
                                          self.env.ref('core.supplier_category_1').id)
        # 发票号码： % s未下推生成采购订单！ 报错
        with self.assertRaises(UserError):
            self.tax_invoice_in.tax_invoice_done()
        # 正常生成采购订单然后审核
        self.tax_invoice_in.invoice_to_buy()
        # self.tax_invoice_in.tax_invoice_done()

        # 反审核 进项发票
        # self.tax_invoice_in.tax_invoice_draft()
