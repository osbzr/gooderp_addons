# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class test_cn_account_invoice(TransactionCase):
    def setUp(self):
        ''' setUp data '''
        super(test_cn_account_invoice, self).setUp()
        self.env['ir.values'].set_default('tax.config.settings',
                                          'default_goods_supplier',
                                          self.env.ref('core.supplier_category_1').id)
        self.cn_invoice = self.env['cn.account.invoice'].create({
            'type': 'in',
            'invoice_type': 'zy',
            'invoice_date': '2016-05-25',
            'invoice_code': '222222',
            'name': '888888',
            'partner_name_in': '开阖',
            'partner_code_in': '922T',
            'partner_address_in': '金海路2588B213',
            'partner_bank_number_in': '建行6217 8888 8888',
        })
        self.cn_invoice_line = self.env['cn.account.invoice.line'].create({
            'product_name': '玉米',
            'product_unit': '斤',
            'product_count': 1.0,
            'product_price': 2.0,
            'product_amount': 2.0,
            'product_tax_rate': 11,
            'product_tax': 0.22,
            'tax_type': '1010101030000000000',
        })
        self.cn_invoice_line.order_id = self.cn_invoice.id

    def test_action_get_attachment_view(self):
        ''' Uploading attachments of expense invoice '''
        self.cn_invoice.action_get_attachment_view()

    def test_compute_attachment_number(self):
        ''' Test: _compute_attachment_number  '''
        self.cn_invoice._compute_attachment_number()

    def test_create_buy_partner(self):
        ''' Test: create buy partner '''
        self.cn_invoice.create_buy_partner()

    def test_create_buy_partner_same_main_mobile_and_tax_num(self):
        ''' Test: create buy partner,.main_mobile, tax_num same '''
        #
        self.cn_invoice.partner_address_in = '金海路922T'
        self.cn_invoice.create_buy_partner()

        self.cn_invoice.create_buy_partner()

    def test_create_category(self):
        ''' Test: create category '''
        self.cn_invoice.create_category()

    def test_create_product(self):
        ''' Test: create product '''
        # 商品 uom_id 必须存在
        self.cn_invoice_line.product_unit = '件'
        # 商品 category_id 必须存在
        self.cn_invoice_line.tax_type = '不征税自来水'
        self.env.ref('core.goods_category_1').tax_category_id = self.env.ref('tax.nsbm6110000000000000000').id

        self.cn_invoice.create_product()

    def test_create_sell_partner(self):
        ''' Test: create_sell_partner '''
        # 创建客户，但是不存在 客户类别 报错
        with self.assertRaises(UserError):
            self.cn_invoice.create_sell_partner()

        # 主要手机号和税号相同
        self.env['ir.values'].set_default('tax.config.settings', 'default_customer',
                                          self.env.ref('tax.domestic_customer').id)
        self.cn_invoice.partner_name_out = 'kaihe'
        self.cn_invoice.partner_address_out = '金海路922T'
        self.cn_invoice.partner_code_out = '922T'
        self.cn_invoice.create_sell_partner()
