# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import datetime


class TestReport(TransactionCase):
    def test_bank_report(self):
        ''' 测试银行对账单报表 '''
        # 生成收款单记录
        self.env.ref('money.get_40000').money_order_done()
        # 生成其他收支单记录
        last_balance = self.env.ref('core.comm').balance
        self.env.ref('money.other_get_60').other_money_done()
        # tax_rate = self.env.ref('base.main_company').import_tax_rates
        self.assertAlmostEqual(self.env.ref(
            'core.comm').balance, last_balance + 60.0)
        # 生成转账单记录
        self.env.ref('money.transfer_300').money_transfer_done()
        # 执行向导
        self.env.ref('core.comm').init_balance = 10000
        statement = self.env['bank.statements.report.wizard'].create({'bank_id': self.env.ref('core.comm').id,
                                                                      'from_date': '2016-11-01', 'to_date': '2016-11-03'})
        # 输出报表
        statement.confirm_bank_statements()
        # 测试现金银行对账单向导：'结束日期不能小于开始日期！'
        statement_date_error = self.env['bank.statements.report.wizard'].create({'bank_id': self.env.ref('core.comm').id,
                                                                                 'from_date': '2016-11-03', 'to_date': '2016-11-02'})
        with self.assertRaises(UserError):
            statement_date_error.confirm_bank_statements()
        # 测试现金银行对账单向导：from_date的默认值是否是公司启用日期
        statement_date = self.env['bank.statements.report.wizard'].create({'bank_id': self.env.ref('core.comm').id,
                                                                           'to_date': '2016-11-03'})
        self.assertEqual(statement_date.from_date,
                         self.env.user.company_id.start_date)
        # 查看对账单明细; 同时执行_compute_balance
        statement_money = self.env['bank.statements.report'].search([])
        for money in statement_money:
            self.assertNotEqual(str(money.balance), 'zxy')
            money.find_source_order()

    def test_bank_report_compute_init(self):
        ''' 测试 银行对账单报表 _compute_balance name 为 期初'''
        self.env.ref('money.other_get_60').other_money_done()
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('core.comm').init_balance = 10000
        statement = self.env['bank.statements.report.wizard'].create(
            {'bank_id': self.env.ref('core.comm').id})
        statement.confirm_bank_statements()
        statement_money = self.env['bank.statements.report'].search([])
        for money in statement_money:
            self.assertNotEqual(str(money.balance), 'kaihe')
            money.find_source_order()

    def test_other_money_report(self):
        ''' 测试其他收支单明细表'''
        # 执行向导
        statement = self.env['other.money.statements.report.wizard'].create({'from_date': '2016-11-01',
                                                                             'to_date': '2016-11-03'})
        # 输出报表
        statement.confirm_other_money_statements()
        # 测试其他收支单明细表向导：'结束日期不能小于开始日期！'
        statement_error_date = self.env['other.money.statements.report.wizard'].create({'from_date': '2016-11-03',
                                                                                        'to_date': '2016-11-01'})
        with self.assertRaises(UserError):
            statement_error_date.confirm_other_money_statements()
        # 测试其他收支单明细表向导：from_date的默认值
        statement_date = self.env['other.money.statements.report.wizard'].create(
            {'to_date': '2016-11-03'})
        # 判断from_date的值是否是公司启用日期
        self.assertEqual(statement_date.from_date,
                         self.env.user.company_id.start_date)

    def test_partner_statements_report(self):
        ''' 测试业务伙伴对账单报表'''
        # onchange_from_date 业务伙伴先改为供应商，再改为客户
        self.partner_id = self.env.ref('core.lenovo').id
        self.env['partner.statements.report.wizard'].onchange_from_date()
        self.assertEqual(self.partner_id, self.env.ref('core.lenovo').id)
        self.partner_id = self.env.ref('core.jd').id
        self.env['partner.statements.report.wizard'].with_context(
            {'default_customer': True}).onchange_from_date()
        self.assertEqual(self.partner_id, self.env.ref('core.jd').id)

    def test_money_get_pay_wizard(self):
        """资金收支报表"""
        # 创建向导
        wizard = self.env['money.get.pay.wizard'].create({})
        # 判断date_start的值是否是公司启用日期
        self.assertEqual(wizard.date_start,
                         self.env.user.company_id.start_date)
        # 结束日期不能小于开始日期
        wizard_error = self.env['money.get.pay.wizard'].create({
            'date_start': '2017-04-14',
            'date_end': '2017-04-12',
        })
        with self.assertRaises(UserError):
            wizard_error.button_confirm()
        # 按全部筛选
        wizard.button_confirm()
        # 按其他收入筛选
        wizard.type = 'other_get'
        wizard.button_confirm()

    def test_cash_flow_wizard(self):
        """现金流量表"""
        # 创建向导
        wizard = self.env['cash.flow.wizard'].create({})
        # 判断 period_id 是否是当前月的会计期间
        datetime_str = datetime.now().strftime("%Y-%m-%d")
        datetime_str_list = datetime_str.split('-')
        period_row = self.env['finance.period'].search(
            [('year', '=', datetime_str_list[0]), ('month', '=', str(int(datetime_str_list[1])))])
        current_period = period_row and period_row[0]
        self.assertEqual(wizard.period_id, current_period)
        wizard.show()
