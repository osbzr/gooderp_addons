# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class test_report(TransactionCase):
    
    def setUp(self):
        super(test_report, self).setUp()
        # 审核2015年12月和2016年1月的会计凭证
        self.env.ref('finance.voucher_12').voucher_done()
        self.env.ref('finance.voucher_1').voucher_done()
        self.env.ref('finance.voucher_2').voucher_done()
        # 结转2015年12月的期间
        self.env['checkout.wizard'].create(
                       {'date':'2015-12-31'}).button_checkout()
        self.period_id = self.env.ref('finance.period_201512').id

    def test_trail_balance(self):
        ''' 测试科目余额表 '''
        report = self.env['create.trial.balance.wizard'].create(
            {'period_id': self.period_id}
                    )
        report.create_trial_balance()

    def test_vouchers_summary(self):
        ''' 测试总账和明细账'''
        report = self.env['create.trial.balance.wizard'].create(
            {'period_begin_id': self.period_id,
             'period_end_id': self.period_id,
             'subject_name_id': self.env.ref('finance.account_fund')}
                    )
        report.create_vouchers_summary()
        report.create_general_ledger_account()

    def test_balance_sheet(self):
        ''' 测试科目余额表 '''
        report = self.env['create.balance.sheet.wizard'].create(
            {'period_id': self.period_id}
                    )
        report.create_balance_sheet()
        report.create_profit_statement()
