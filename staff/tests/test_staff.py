# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime,timedelta

class test_staff(TransactionCase):

    def test_get_image(self):
        '''拿到用户头像,职位的onchange'''
        staff_pro = self.env['staff'].create({
                                              'name': 'DemoUser',
                                              'user_id': 1,
                                              'job_id': self.env.ref('staff.staff_job_1').id})
        staff_pro._get_image()
        staff_pro.onchange_job_id()


class test_mail_message(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(test_mail_message, self).setUp()
        self.staff = self.browse_ref('staff.staff_1')

    def test_staff_birthday_message(self):
        '''测试：员工生日当天，whole company 会收到祝福信息'''

        # 设置了员工生日
        self.staff.birthday = datetime.now()
        job = self.browse_ref('staff.ir_cron_module_update_notification_birthday')
        job.interval_type = 'minutes'
        job.nextcall = (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
        job.doall = True
        self.env['mail.message'].staff_birthday_message()
