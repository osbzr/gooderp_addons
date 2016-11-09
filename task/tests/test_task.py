# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import datetime


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


class test_timesheet(TransactionCase):

    def setUp(self):
        super(test_timesheet, self).setUp()
        self.timesheet = self.env.ref('task.timesheet_20161110')

    def test_name_get(self):
        '''测试今日工作日志的name_get'''
        name = self.timesheet.name_get()
        real_name = '%s %s' % (self.env.ref('base.user_root').name, '2016-11-10')
        self.assertEqual(name[0][1], real_name)


class test_timeline(TransactionCase):

    def setUp(self):
        super(test_timeline, self).setUp()
        self.task = self.env.ref('task.task_sell')
        self.status_doing = self.env.ref('task.task_status_doing')

    def test_create(self):
        '''创建工作记录时应更新对应task的status等字段'''
        timeline = self.env['timeline'].create({
            'task_id': self.task.id,
            'just_done': u'创建一个销货订单',
            'next_action': u'测试其他内容',
            'next_datetime': (datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            'set_status': self.status_doing.id,
        })
        self.assertEqual(self.task.status, self.status_doing)
        self.assertEqual(self.task.next_action, timeline.next_action)
        self.assertEqual(self.task.next_datetime, timeline.next_datetime)
