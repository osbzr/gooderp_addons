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
        self.assertTrue(hire.stage_id == self.env.ref('staff_hire.stage_job1'))
        # 没有阶段时创建招聘
        self.env['staff.hire.stage'].search([]).unlink()
        hire = self.env['hire.applicant'].create({
            'partner_name': u'小赵',
            'partner_mobile': '188188188',
            'job_id': self.env.ref('staff.staff_job_1').id,
        })
        self.assertTrue(not hire.stage_id)

    def test_onchange_job_id(self):
        '''选择职位，带出部门、负责人及阶段'''
        self.hire.onchange_job_id()
        self.assertTrue(self.hire.department_id == self.env.ref('staff.department_1'))

    def test_create_employee_from_applicant(self):
        '''创建员工'''
        self.hire.create_employee_from_applicant()
        self.assertTrue(self.hire.staff_id.name == 'Lucy')
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
        self.assertTrue(action['res_id'] == self.hire.staff_id.id)

    def test_track_subtype(self):
        '''员工或阶段变更时消息作相应更新'''
        self.hire.stage_id = self.env.ref('staff_hire.stage_job2')

    def test_action_makeMeeting(self):
        '''打开会议的日历视图来安排当前申请人的会议'''
        self.hire.action_makeMeeting()

    def test_archive_applicant(self):
        '''拒绝'''
        self.hire.archive_applicant()
        self.assertTrue(not self.hire.active)
        # 重复拒绝报错
        with self.assertRaises(UserError):
            self.hire.archive_applicant()

    def test_reset_applicant(self):
        '''重新打开'''
        self.hire.archive_applicant()
        self.hire.reset_applicant()
        self.assertTrue(self.hire.stage_id == self.env.ref('staff_hire.stage_job1'))
        # 重复重新打开报错
        with self.assertRaises(UserError):
            self.hire.reset_applicant()

    def test_action_get_attachment_tree_view(self):
        '''查看简历计算简历个数'''
        self.hire.action_get_attachment_tree_view()
        self.hire._get_attachment_number()
        self.assertTrue(self.hire.attachment_number == 0)

    def test_read_group_stage_ids(self):
        stages = self.env['staff.hire.stage'].search([])
        self.hire._read_group_stage_ids(stages=stages, domain=[], order='sequence')
