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

        # 不能重复确认
        with self.assertRaises(UserError):
            self.expense_line.hr_expense_line_confirm()

    def test_hr_expense_line_draft(self):
        ''' Anti audit expense invoice '''
        self.expense_line.hr_expense_line_confirm()
        self.expense_line.hr_expense_line_draft()

        # 不能重复撤销
        with self.assertRaises(UserError):
            self.expense_line.hr_expense_line_draft()

    def test_hr_expense_line_draft_has_order_ref(self):
        ''' Test:  hr_expense_line_draft, the expense line exists order_id'''
        expense = self.env['hr.expense'].create({
            'staff': self.env.ref('staff.lili').id,
            'type': 'my',
            'bank_account_id': self.env.ref('core.comm').id
        })
        self.expense_line.order_id = expense.id
        self.expense_line.hr_expense_line_confirm()
        # 请先解除关联单据 报错
        with self.assertRaises(UserError):
            self.expense_line.hr_expense_line_draft()

    def test_action_get_attachment_view(self):
        ''' Uploading attachments of expense invoice '''
        self.expense_line.action_get_attachment_view()

    def test_saomiaofapiao(self):
        ''' Test: saomiaofapiao  '''
        model_name = 'hr.expense.line'
        order_id = self.expense_line.id

        # 请确认扫描是否正确 报错
        barcode = '01,10,033001600211,11255692'
        with self.assertRaises(UserError):
            self.expense_line.saomiaofapiao(model_name, barcode, order_id)

        barcode = '01,10,033001600211,11255692,349997.85,20180227,62521957050111533932,7DF9,'
        self.expense_line.saomiaofapiao(model_name, barcode, order_id)

        barcode = '01,01,033001600211,11255692,349997.85,20180227,62521957050111533932,7DF9,'
        self.expense_line.saomiaofapiao(model_name, barcode, order_id)

        barcode = '01,04,033001600211,11255692,349997.85,20180227,62521957050111533932,7DF9,'
        self.expense_line.saomiaofapiao(model_name, barcode, order_id)

    def test_unlink(self):
        ''' Test: unlink  '''
        # 只能删除草稿状态的费用发票
        with self.assertRaises(UserError):
            self.expense_line.hr_expense_line_confirm()
            self.expense_line.unlink()
        self.expense_line.hr_expense_line_draft()
        self.expense_line.unlink()

    def test_compute_attachment_number(self):
        ''' Test: _compute_attachment_number  '''
        self.expense_line._compute_attachment_number()


class TestHrExpense(TransactionCase):
    def setUp(self):
        ''' setUp data '''
        super(TestHrExpense, self).setUp()
        money_40000 = self.env.ref('money.get_40000')
        money_40000.money_order_done()
        self.expense_line = self.env.ref('staff_expense.employee_expense_1')
        self.expense_line.invoice_name = '666'
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

        # 不能重复确认
        with self.assertRaises(UserError):
            self.expense.hr_expense_confirm()

        self.expense.hr_expense_draft()
        self.expense_line.invoice_type = 'zy'
        self.expense.hr_expense_confirm()

    def test_hr_expense_confirm_to_company(self):
        ''' Audit employee reimbursement: to company '''
        # 支付方式是 付给公司
        self.expense.type = 'company'
        self.expense.partner_id = self.env.ref('core.lenovo').id
        self.expense_line.invoice_type = 'zy'
        self.expense.hr_expense_confirm()

    def test_hr_expense_draft_to_employee(self):
        ''' Anti audit expense invoice: to employee '''
        self.expense.hr_expense_confirm()
        # 反审核员工报销
        self.expense.hr_expense_draft()

        # 不能重复撤销
        with self.assertRaises(UserError):
            self.expense.hr_expense_draft()

    def test_hr_expense_draft_to_company(self):
        ''' Anti audit expense invoice: to company '''
        self.expense.type = 'company'
        self.expense.partner_id = self.env.ref('core.lenovo').id
        self.expense.hr_expense_confirm()
        # 反审核员工报销
        self.expense.hr_expense_draft()

    def test_unlink(self):
        ''' Test: unlink  '''
        # 只能删除草稿状态的费用报销单
        with self.assertRaises(UserError):
            self.expense.hr_expense_confirm()
            self.expense.unlink()
        self.expense.hr_expense_draft()
        self.expense.unlink()

    def test_state_to_done(self):
        ''' Test: _state_to_done  '''
        self.expense.hr_expense_confirm()
        self.expense.other_money_order.other_money_done()

        # hr_expense_draft: other_money_order state = 'done'
        self.expense.hr_expense_draft()

    def test_check_consistency(self):
        ''' Test: check_consistency '''
        expense_line_1 = self.env.ref('staff_expense.employee_expense_2')
        expense_line_1.order_id = self.expense.id
        # 费用明细必须是同一人 报错
        with self.assertRaises(UserError):
            self.expense.write({})

        # 申报支付给公司的费用必须同一类别！ 报错
        expense_line_1.staff = self.env.ref('staff.lili').id
        expense_line_1.category_id = self.env.ref('core.cat_consult').id
        with self.assertRaises(UserError):
            self.expense.type = 'company'
