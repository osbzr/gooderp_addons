# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestHireApplicant(TransactionCase):

    def setUp(self):
        super(TestHireApplicant, self).setUp()
        self.hire = self.env.ref('staff_hire.hire_lucy')

    def test_action_start_survey(self):
        '''开始面试'''
        self.hire.action_start_survey()
        # 有负责人
        self.hire.user_id = self.env.uid
        self.hire.action_start_survey()
