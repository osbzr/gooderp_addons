# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestReportDocxPartner(TransactionCase):
    def setUp(self):
        ''' 准备数据 '''
        super(TestReportDocxPartner, self).setUp()
        self.ir_actions_supplier = self.env.ref('money.report_supplier_statements_report')
        self.report_docx_supplier = self.ir_actions_supplier._lookup_report('supplier.statements.report')
        self.money_order_supplier = self.env.ref('money.pay_2000')

        self.ir_actions_customer = self.env.ref('money.report_customer_statements_report')
        self.report_docx_customer = self.ir_actions_customer._lookup_report('customer.statements.report')
        self.money_order_customer = self.env.ref('money.get_40000')

    def test_lookup_report(self):
        ''' 测试 客户/供应商对账单 docx报表 '''
        # 无 customer.statements.report 记录
        self.report_docx_customer.create(
            self.cr, self.uid, self.money_order_customer.id, self.ir_actions_customer, self.env.context)

        # 无 supplier.statements.report 记录
        self.report_docx_supplier.create(
            self.cr, self.uid, self.money_order_supplier.id, self.ir_actions_supplier, self.env.context)

        # 有 customer.statements.report 记录
        self.money_order_customer.money_order_done()
        ctx_customer = self.env.context.copy()
        ctx_customer['partner_id'] = self.env.ref('core.jd').id
        ctx_customer['from_date'] = '2016-02-18'
        ctx_customer['to_date'] = '2016-02-21'
        self.report_docx_customer.create(
            self.cr, self.uid, self.money_order_customer.id, self.ir_actions_customer, ctx_customer)

        # 有 customer.statements.report 记录, 但记录在开始日期前
        ctx_customer['from_date'] = '2016-02-21'
        ctx_customer['to_date'] = '2016-02-22'
        self.report_docx_customer.create(
            self.cr, self.uid, self.money_order_customer.id, self.ir_actions_customer, ctx_customer)

        # 有 supplier.statements.report 记录
        self.money_order_supplier.money_order_done()
        ctx_supplier = self.env.context.copy()
        ctx_supplier['partner_id'] = self.env.ref('core.lenovo').id
        ctx_supplier['from_date'] = '2016-02-18'
        ctx_supplier['to_date'] = '2016-02-21'
        self.report_docx_supplier.create(
            self.cr, self.uid, self.money_order_supplier.id, self.ir_actions_supplier, ctx_supplier)

        # 有 supplier.statements.report 记录, 但记录在开始日期前
        ctx_supplier['from_date'] = '2016-02-21'
        ctx_supplier['to_date'] = '2016-02-22'
        self.report_docx_supplier.create(
            self.cr, self.uid, self.money_order_supplier.id, self.ir_actions_supplier, ctx_supplier)

