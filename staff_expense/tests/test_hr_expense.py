# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class TestHrExpenseLine(TransactionCase):
    def setUp(self):
        ''' setUp data '''
        super(TestHrExpenseLine, self).setUp()
        self.expense_line = self.env.ref('staff_expense.employee_expense_1')

    def test_hr_expense_line_confirm(self):
        ''' Audit expense invoice '''
        self.expense_line.hr_expense_line_confirm()

    def test_hr_expense_line_draft(self):
        ''' Anti audit expense invoice '''
        self.expense_line.hr_expense_line_confirm()
        self.expense_line.hr_expense_line_draft()

    def test_action_get_attachment_view(self):
        ''' Uploading attachments of expense invoice '''
        self.expense_line.action_get_attachment_view()


class TestHrExpense(TransactionCase):
    def setUp(self):
        ''' setUp data '''
        super(TestHrExpense, self).setUp()
        money_40000 = self.env.ref('money.get_40000')
        money_40000.money_order_done()
        self.expense_line = self.env.ref('staff_expense.employee_expense_1')
        self.expense_line.hr_expense_line_confirm()
        self.expense = self.env['hr.expense'].create({
            'staff': self.env.ref('staff.lili').id,
            'type': 'my',
            'bank_account_id': self.env.ref('core.comm').id
        })
        self.expense_line.order_id = self.expense.id

    def test_hr_expense_confirm_to_employee(self):
        ''' Audit employee reimbursement: to employee '''
        # 支付方式是 付给报销人
        self.expense.hr_expense_confirm()

    def test_hr_expense_confirm_to_company(self):
        ''' Audit employee reimbursement: to company '''
        # 支付方式是 付给公司
        self.expense.type = 'company'
        self.expense.partner_id = self.env.ref('core.lenovo').id
        self.expense.hr_expense_confirm()

    def test_hr_expense_draft_to_employee(self):
        ''' Anti audit expense invoice: to employee '''
        self.expense.hr_expense_confirm()
        # 反审核员工报销
        self.expense.hr_expense_draft()

    def test_hr_expense_draft_to_company(self):
        ''' Anti audit expense invoice: to company '''
        self.expense.type = 'company'
        self.expense.partner_id = self.env.ref('core.lenovo').id
        self.expense.hr_expense_confirm()
        # 反审核员工报销
        self.expense.hr_expense_draft()
