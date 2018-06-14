# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestStaff(TransactionCase):

    def setUp(self):
        super(TestStaff, self).setUp()
        self.hire = self.env.ref('staff_hire.hire_lucy')
        self.hire.onchange_job_id()
        self.hire.create_employee_from_applicant()
        self.staff_lucy = self.env['staff'].search([('name', '=', 'Lucy')])

    def test_compute_newly_hired_staff(self):
        '''计算新进员工数'''
        self.assertTrue(self.staff_lucy.newly_hired_staff)

    def test_search_newly_hired_staff(self):
        self.staff_lucy._search_newly_hired_staff(operator='=', value='lucy')
