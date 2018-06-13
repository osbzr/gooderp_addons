# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestHireApplicant(TransactionCase):

    def setUp(self):
        super(TestHireApplicant, self).setUp()
        self.hire = self.env.ref('staff_hire.hire_lucy')

    def test_default_stage_id(self):
        '''返回阶段的默认值'''
        hire = self.env['hire.applicant'].create({
            'partner_name': u'小赵',
            'partner_mobile': '188188188',
            'job_id': self.env.ref('staff.staff_job_1').id,
        })

    def test_onchange_job_id(self):
        '''选择职位，带出部门、负责人及阶段'''
        self.hire.onchange_job_id()
        self.assertTrue(self.hire.department_id, self.env.ref('staff.department_1'))

    def test_create_employee_from_applicant(self):
        '''创建员工'''
        self.hire.create_employee_from_applicant()
        self.assertTrue(self.hire.staff_id.name, 'Lucy')
        self.hire.action_get_created_employee()
        # 期望薪资未输入时应报错
        hire = self.hire.copy()
        hire.salary_proposed = 0
        with self.assertRaises(UserError):
            hire.create_employee_from_applicant()

    def test_action_get_created_employee(self):
        '''跳到新创建的员工界面'''
        self.hire.create_employee_from_applicant()
        action = self.hire.action_get_created_employee()
        self.assertTrue(action['res_id'], self.hire.staff_id.id)
