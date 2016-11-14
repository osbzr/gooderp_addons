# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class test_staff(TransactionCase):

    def test_get_image(self):
        '''拿到用户头像,职位的onchange'''
        staff_pro = self.env['staff'].create({
                                              'identification_id':111111,
                                              'work_phone':12345678901,
                                              'name': 'DemoUser',
                                              'user_id': 1,
                                              'job_id': self.env.ref('staff.staff_job_1').id})
        staff_pro._get_image()
        staff_pro.onchange_job_id()

    def test_staff_contract_over_date(self):
        '''测试：员工合同到期，发送邮件给员工 和 部门经理（如果存在）'''

        job = self.browse_ref('staff.ir_cron_module_remind_contract_over_date')
        job.interval_type = 'minutes'
        job.nextcall = (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
        job.doall = True
        # not staff.contract_ids
        self.env['staff'].staff_contract_over_date()

        # has staff.contract_ids but no apartment manager
        staff_lily = self.env.ref('core.lili')
        staff_lily.work_email = 'lili@sina.com.cn'
        staff_lily.contract_ids.create({'staff_id': staff_lily.id,
                                        'basic_wage': 123456,
                                        'over_date': datetime.now().strftime("%Y-%m-%d"),
                                        'job_id': self.env.ref('staff.staff_job_1').id})

        # has staff.contract_ids and apartment manager
        self.env.ref('staff.staff_1').work_email = 'admin@sina.com.cn'
        staff_lily.parent_id = self.env.ref('staff.staff_1').id
        self.env['staff'].staff_contract_over_date()


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
