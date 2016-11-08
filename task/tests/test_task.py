# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class test_task(TransactionCase):

    def setUp(self):
        super(test_task, self).setUp()
        self.task = self.env.ref('task.task_sell')

    def test_compute_hours(self):
        '''计算任务的实际时间'''
        self.assertTrue(self.task.hours == 1)

    def test_assign_to_me(self):
        '''将任务指派给自己，并修改状态'''
        self.task.assign_to_me()
        self.assertTrue(self.task.user_id == self.env.ref('base.user_root'))
        self.assertTrue(self.task.status == self.env.ref('task.task_status_doing'))
