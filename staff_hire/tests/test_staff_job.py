# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestStaffJob(TransactionCase):

    def setUp(self):
        super(TestStaffJob, self).setUp()
        self.hire = self.env.ref('staff_hire.hire_lucy')
        self.hire.onchange_job_id()
        self.job_id = self.env.ref('staff.staff_job_1')

    def test_default_address_id(self):
        '''默认工作地点'''
        hire = self.env['staff.job'].create({
            'name': u'hr',
            'department_id': self.env.ref('staff.department_1').id,
        })
        self.assertTrue(hire.address_id == self.env.user.company_id)

    def test_compute_employees(self):
        '''计算该职位员工个数'''
        self.hire.create_employee_from_applicant()
        self.assertTrue(self.job_id.no_of_employee == 1)

    def test_compute_document_ids(self):
        '''计算该职位简历数'''
        # 在招聘模型上上传简历
        self.env['ir.attachment'].create({
            'name': u'Lucy 的简历',
            'res_model': 'hire.applicant',
            'res_id': self.hire.id,
        })
        self.job_id._compute_document_ids()
        self.assertTrue(self.job_id.documents_count == 1)
        # 在职位模型上上传简历
        self.env['ir.attachment'].create({
            'name': u'Lucy 的简历',
            'res_model': 'staff.job',
            'res_id': self.job_id.id,
        })
        self.job_id._compute_document_ids()
        self.assertTrue(self.job_id.documents_count == 2)

    def test_compute_application_count(self):
        '''计算该职位招聘数'''
        self.job_id._compute_application_count()
        self.assertTrue(self.job_id.application_count == 1)

    def test_action_get_attachment_tree_view(self):
        '''跳转到简历界面'''
        self.job_id.action_get_attachment_tree_view()

    def test_set_open(self):
        '''启动招聘'''
        self.job_id.set_close()
        self.job_id.set_open()
        self.assertTrue(self.job_id.state == 'open')
        # 重复操作报错
        with self.assertRaises(UserError):
            self.job_id.set_open()

    def test_set_close(self):
        '''结束招聘'''
        self.job_id.set_close()
        self.assertTrue(self.job_id.state == 'close')
        # 重复操作报错
        with self.assertRaises(UserError):
            self.job_id.set_close()
