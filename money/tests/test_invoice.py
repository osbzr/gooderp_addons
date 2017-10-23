# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestInvoice(TransactionCase):

    def setUp(self):
        '''依赖设置'''
        super(TestInvoice, self).setUp()
        # 客户分类
        self.cate = self.env['core.category'].create({
            'name': '测试客户',
            'account_id': self.env.ref("finance.account_ar").id,
            'type': 'customer',
        })
        self.partner = self.env['partner'].create({
            'name': 'Jeff',
            'c_category_id': self.cate.id,
            'main_mobile': '14957236658',
        })

    def tearDown(self):
        '''依赖移除'''
        self.partner.unlink()
        self.cate.unlink()
        super(TestInvoice, self).tearDown()

    def test_create_delete(self):
        '''测试发票创建和删除'''
        # 创建发票
        invoice = self.env['money.invoice'].create({'name': 'new_test_invoice',
                                                    'partner_id': self.partner.id, 'date': "2016-02-20",
                                                    'category_id': self.env.ref('money.core_category_sale').id,
                                                    'amount': 10.0})
        # 如果公司的 draft_invoice参数未设，发票自动审核
        if self.env.ref('base.main_company').draft_invoice:
            self.assertEqual(invoice.state, 'draft')
            # 发票审核
            invoice.money_invoice_done()

        # 确认发票为已审核状态
        self.assertEqual(invoice.state, 'done')
        # 客户的应收余额
        self.assertEqual(self.partner.receivable, 10.0)
        # 已审核的发票应该不可删除
        with self.assertRaises(UserError):
            invoice.unlink()
        # 发票取消审核
        invoice.money_invoice_draft()
        # 客户的应收余额
        self.assertEqual(self.partner.receivable, 0.0)
        # 未审核的发票可以删除
        invoice.unlink()
        supplier = self.env.ref('core.lenovo')
        supplier.s_category_id.account_id = self.env.ref(
            "finance.account_ap").id
        # 执行money_invoice_draft()的if category_id.type == 'expense'
        invoice_buy = self.env['money.invoice'].create({'name': 'buy_invoice', 'date': "2016-02-20",
                                                        'partner_id': supplier.id,
                                                        'category_id': self.env.ref('money.core_category_purchase').id,
                                                        'amount': 10.0})
        invoice_buy.money_invoice_done()
        invoice_buy.money_invoice_draft()

    def test_money_invoice_draft_voucher_done(self):
        '''发票生成的凭证已审核时，反审核发票'''
        supplier = self.env.ref('core.lenovo')
        supplier.s_category_id.account_id = self.env.ref(
            "finance.account_ap").id
        invoice_buy = self.env['money.invoice'].create({'name': 'buy_invoice', 'date': "2016-02-20",
                                                        'partner_id': supplier.id,
                                                        'category_id': self.env.ref('money.core_category_purchase').id,
                                                        'amount': 10.0})
        invoice_buy.money_invoice_done()
        invoice_buy.money_invoice_draft()

    def test_money_invoice_voucher_line_currency(self):
        ''' 创建凭证行时，invoice与公司的币别不同的情况 '''
        invoice = self.env['money.invoice'].create({
            'name': 'invoice', 'date': "2016-02-20",
            'partner_id': self.env.ref('core.jd').id,
            'category_id': self.env.ref('money.core_category_sale').id,
            'amount': 10.0,
            'currency_id': self.env.ref('base.USD').id})
        invoice.money_invoice_done()

    def test_money_invoice_company_no_tax_account(self):
        ''' 创建 进项税行 公司 进项税科目 未设置 '''
        # 进项税行 import_tax_account
        buy_invoice = self.env['money.invoice'].create({
            'name': 'invoice', 'date': "2016-02-20",
            'partner_id': self.env.ref('core.lenovo').id,
            'category_id': self.env.ref('money.core_category_purchase').id,
            'amount': 10.0,
            'tax_amount': 11.7})
        self.env.user.company_id.import_tax_account = False
        with self.assertRaises(UserError):
            buy_invoice.money_invoice_done()
        # 销项税行 output_tax_account
        sell_invoice = self.env['money.invoice'].create({
            'name': 'invoice', 'date': "2016-02-20",
            'partner_id': self.env.ref('core.jd').id,
            'category_id': self.env.ref('money.core_category_sale').id,
            'amount': 10.0,
            'tax_amount': 11.7})
        self.env.user.company_id.output_tax_account = False
        with self.assertRaises(UserError):
            sell_invoice.money_invoice_done()

    def test_money_invoice_name_get(self):
        ''' 测试 money invoice name_get 方法 '''
        inv = self.env['money.invoice'].create({
            'name': 'invoice', 'date': "2016-02-20",
            'partner_id': self.env.ref('core.jd').id,
            'category_id': self.env.ref('money.core_category_sale').id,
            'amount': 10.0,
            'tax_amount': 11.7
        })
        # 发票号不存在取 订单编号
        inv_name = inv.name_get()
        real_name = '%s' % (inv.name)
        self.assertTrue(inv_name[0][1] == real_name)

        # 发票号存在取 发票号
        inv.bill_number = '201600001'
        inv_name_bill = inv.name_get()
        real_name_bill = '%s' % (inv.bill_number)
        self.assertTrue(inv_name_bill[0][1] == real_name_bill)

    def test_money_invoice_compute_overdue(self):
        """
        计算逾期天数、计算逾期金额
        """
        invoice = self.env['money.invoice'].create({
            'name': 'invoice', 'date': "2016-02-20",
            'partner_id': self.env.ref('core.jd').id,
            'category_id': self.env.ref('money.core_category_sale').id,
            'amount': 117,
            'tax_amount': 17,
            'date_due': '2016-04-10',
        })
        self.assertEqual(invoice.overdue_amount, 117)
