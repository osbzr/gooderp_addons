# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class test_trial_balance(TransactionCase):

    def setUp(self):
        super(test_trial_balance, self).setUp()
        self.period_last_year = self.env.ref('finance.period_201512')
        self.period_first_year = self.env.ref('finance.period_201601')
        self.period_201511 = self.env.ref('finance.period_201511')
        self.period_last = self.env.ref('finance.period_201603')
        self.period_now = self.env.ref('finance.period_201604')

        subject_name_id_1 = self.env.ref('finance.finance_account_1')
        subject_name_id_4 = self.env.ref('finance.finance_account_4')
        # subject_name_id_11 = self.env.ref('finance.finance_account_11')
        self.trial_balance_wizard_now = self.env['create.trial.balance.wizard'].create({'period_id': self.period_now.id})
        self.trial_balance_wizard_last = self.env['create.trial.balance.wizard'].create({'period_id': self.period_last.id})
        # self.trial_balance_wizard_period_first_year = self.env['create.trial.balance.wizard'].create({'period_id': self.period_first_year.id})
        self.trial_balance_wizard_period_last_year = self.env['create.trial.balance.wizard'].create({'period_id': self.period_last_year.id})
        self.period_201511_wizard = self.env['create.trial.balance.wizard'].create({'period_id': self.period_201511.id})

        self.period_2016__01_03 = self.env['create.vouchers.summary.wizard'].create({'period_begin_id': self.period_last.id,
                                                                                     'period_end_id': self.period_last.id, 'subject_name_id': subject_name_id_1.id})
        self.period_2016_01_04 = self.env['create.vouchers.summary.wizard'].create({'period_begin_id': self.period_first_year.id,
                                                                                    'period_end_id': self.period_now.id, 'subject_name_id': subject_name_id_1.id})
        self.period_2016_01_03_04 = self.env['create.vouchers.summary.wizard'].create({'period_begin_id': self.period_last.id,
                                                                                       'period_end_id': self.period_now.id, 'subject_name_id': subject_name_id_1.id})
        self.period_2016_01_04_04 = self.env['create.vouchers.summary.wizard'].create({'period_begin_id': self.period_last.id,
                                                                                       'period_end_id': self.period_now.id, 'subject_name_id': subject_name_id_1.id})
        self.period_2016_04_04 = self.env['create.vouchers.summary.wizard'].create({'period_begin_id': self.period_now.id,
                                                                                    'period_end_id': self.period_now.id, 'subject_name_id': subject_name_id_4.id})

        self.period_2016_11_03 = self.env['create.vouchers.summary.wizard'].create({'period_begin_id': self.period_last.id,
                                                                                    'period_end_id': self.period_now.id, 'subject_name_id': subject_name_id_4.id})

        self.balance_sheet_1 = self.env['balance.sheet'].create({'balance': '货币资金', 'line_num': 1, 'balance_formula': '1001~1002', 'balance_formula': '1001~1002',
                                                                 'balance_two': '短期借款', 'line_num_two': 12, 'balance_two_formula': '', 'balance_two_formula': '',
                                                                 })

        self.balance_sheet_2 = self.env['balance.sheet'].create({'balance': '应收票据', 'line_num': 2, 'balance_formula': '1602~1702', 'balance_formula': '',
                                                                 'balance_two': '应付账款', 'line_num_two': 13, 'balance_two_formula': '', 'balance_two_formula': '',
                                                                 })

        self.balance_sheet_1 = self.env['profit.statement'].create({'balance': '营业收入', 'line_num': '1', 'occurrence_balance_formula': '1001~1002',
                                                                    'occurrence_balance_formula': '1001~1002'})

        self.balance_sheet_2 = self.env['profit.statement'].create({'balance': '营业成本', 'line_num': '2', 'occurrence_balance_formula': '1001~1121',
                                                                    'occurrence_balance_formula': '1602~1121'})
        self.balance_sheet_3 = self.env['profit.statement'].create({'balance': '营业税金及附加', 'line_num': '3', 'occurrence_balance_formula': '1622~1702',
                                                                    'occurrence_balance_formula': ''})
        self.balance_sheet_wizard = self.env['create.balance.sheet.wizard'].create({'period_id': self.period_now.id})
        self.balance_sheet_wizard_last = self.env['create.balance.sheet.wizard'].create({'period_id': self.period_last.id})

    def test_creare_trial_balance(self):
        '''创建科目余额表'''

        self.env['create.trial.balance.wizard'].compute_last_period_id(self.period_first_year)
        self.env['create.trial.balance.wizard'].compute_next_period_id(self.period_last_year)
        self.env['create.trial.balance.wizard'].compute_last_period_id(self.period_last)
        self.env['create.trial.balance.wizard'].compute_next_period_id(self.period_last)
        with self.assertRaises(UserError):
            self.period_201511_wizard.create_trial_balance()
        self.trial_balance_wizard_last.create_trial_balance()
        self.period_last.is_closed = True
        self.trial_balance_wizard_now.create_trial_balance()

        with self.assertRaises(UserError):
            self.trial_balance_wizard_period_last_year.create_trial_balance()

    def test_create_vouchers_summary(self):
        """测试创建明细帐"""
        self.period_2016__01_03.create_vouchers_summary()
        self.period_last.is_closed = True

        self.period_2016_01_03_04.create_vouchers_summary()
        self.period_2016_04_04.create_vouchers_summary()
        with self.assertRaises(UserError):
            self.period_2016_01_04.create_vouchers_summary()

        self.period_2016__01_03.period_end_id = self.period_201511.id
        self.period_2016__01_03.onchange_period()
        self.period_2016__01_03.period_begin_id = self.period_201511.id
        with self.assertRaises(UserError):
            self.period_2016__01_03.create_vouchers_summary()
        self.period_last.is_closed = False
        self.period_2016_11_03.create_vouchers_summary()
        #   22 24

    def test_creare_balance_sheet(self):
        """测试 创建资产负债表"""
        self.balance_sheet_wizard_last.create_balance_sheet()
        self.period_last.is_closed = True
        self.balance_sheet_wizard.create_balance_sheet()

    def test_create_profit_statement(self):
        """测试 创建利润表"""
        self.balance_sheet_wizard_last.create_balance_sheet()
        self.period_last.is_closed = True
        self.balance_sheet_wizard.create_profit_statement()

    def test_default_period(self):
        self.env['create.trial.balance.wizard']._default_peroid_id()
        self.env['create.vouchers.summary.wizard']._default_end_peroid_id()
        self.env['create.vouchers.summary.wizard']._default_begin_peroid_id()
        self.env['create.vouchers.summary.wizard']._default_subject_name_id()
        self.env['create.vouchers.summary.wizard']._default_subject_name_end_id()
        vouchers_summary_row = self.env['create.vouchers.summary.wizard'].create({
                'period_begin_id':self.period_now.id,
                'period_end_id':self.period_last.id, })
        with self.assertRaises(UserError):
            vouchers_summary_row.onchange_period()


