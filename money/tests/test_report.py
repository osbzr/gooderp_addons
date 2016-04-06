# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_report(TransactionCase):
    def test_bank_report(self):
        ''' 测试银行对账单报表 '''
        # 执行向导
        statement = self.env['bank.statements.report.wizard'].create(
                    {'bank_id': self.env.ref('money.money_order_line_1').bank_id.id,
                    'from_date': '2016-11-01',
                    'to_date': '2016-11-03'})
        statement_other = self.env['bank.statements.report.wizard'].create(
                    {'bank_id': self.env.ref('money.bank_report_other_2').bank_id.id,
                    'from_date': '2016-11-01',
                    'to_date': '2016-11-03'})
        statement_transfer_out = self.env['bank.statements.report.wizard'].create(
                    {'bank_id': self.env.ref('money.transfer_order_line').out_bank_id.id,
                    'from_date': '2016-11-01',
                    'to_date': '2016-11-03'})
        statement_transfer_in = self.env['bank.statements.report.wizard'].create(
                    {'bank_id': self.env.ref('money.transfer_order_line').in_bank_id.id,
                    'from_date': '2016-11-01',
                    'to_date': '2016-11-03'})
        # 输出报表
        statement.confirm_bank_statements()
        statement_other.confirm_bank_statements()
        statement_transfer_out.confirm_bank_statements()
        statement_transfer_in.confirm_bank_statements()
        # 查看对账单明细
        self.env['bank.statements.report'].search([('name','=','GET/2016/0001')]).find_source_order()
        self.env['bank.statements.report'].search([('name','=','OTHER_GET/2016/0001')]).find_source_order()
        self.env['bank.statements.report'].search([('name','=','TR/2016/0001')]).find_source_order()

    def test_other_money_report(self):
        ''' 测试其他收支单明细表'''
        # 执行向导
        statement = self.env['other.money.statements.report.wizard'].create(
                    {'from_date': '2016-11-01',
                    'to_date': '2016-11-03'})
        # 输出报表
        statement.confirm_other_money_statements()
        # 测试其他收支单明细表方法中的'结束日期不能小于开始日期！'
        statement_error_date = self.env['other.money.statements.report.wizard'].create(
                    {'from_date': '2016-11-03',
                     'to_date': '2016-11-01'})
        # 输出报表，执行if
        with self.assertRaises(except_orm):
            statement_error_date.confirm_other_money_statements()
        # 测试其他收支单明细表方法中的from_date的默认值
        statement_date = self.env['other.money.statements.report.wizard'].create(
                    {'to_date': '2016-11-03'})
        # 判断from_date的值是否是公司启用日期
        self.assertEqual(statement_date.from_date, self.env.user.company_id.start_date)

    def test_partner_statements_report(self):
        ''' 测试业务伙伴对账单报表'''
        # onchange_from_date
        self.env.ref('money.partner_wizard_pay_400').onchange_from_date()
        