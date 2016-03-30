# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class test_invoice(TransactionCase):

    def setUp(self):
        '''依赖设置'''
        super(TestInvoice, self).setUp()
        # 客户分类
        self.cate = self.env['core.category'].create({
            'name':'测试客户',
            'type':'customer',
            })
        self.partner = self.env['partner'].create({
            'name':'Jeff',
            'c_category_id':self.cate.id,
        })
    
    def tearDown(self):
        '''依赖移除'''
        self.partner.unlink()
        self.cate.unlink()
        super(TestAuditlog, self).tearDown()

    def test_create_delete(self):
        '''测试发票创建和删除'''
        # 创建发票
        invoice = self.env['money.invoice'].create({
            'partner_id':self.partner_id.id,
            'category_id':self.env.ref('core_category_sale').id,
            'amount':10.0,
            })
        # 如果公司的 draft_invoice参数未设，发票自动审核
        if self.env.User.company_id.draft_invoice:
            self.assertEqual(invoice.state, 'draft')
            # 发票审核
            invoice.money_invoice_done()
        # 确认发票为已审核状态
        self.assertEqual(invoice.state, 'done')
        # 客户的应收余额
        self.assertEqual(self.partner.recievable, 10.0)
        # 已审核的发票应该不可删除
        with self.assertRaises(ValidationError):
            invoice.unlink()
        # 发票取消审核
        invoice.money_invoice_draft()
        # 客户的应收余额
        self.assertEqual(self.partner.recievable, 0.0)
        # 未审核的发票可以删除
        invoice.unlink()
