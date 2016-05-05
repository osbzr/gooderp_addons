# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm, ValidationError


class test_staff(TransactionCase):
    
    def test_get_image(self):
        '''拿到用户头像'''
        staff_pro = self.env['staff'].create({
                                              'name':'DemoUser',
                                              'user_id':1})
        staff_pro._get_image()
        

class test_staff_holiday(TransactionCase):

    def test_onchange_days(self):
        '''输入日期改变持续天数'''
        holiday=self.env['staff.holidays'].create({
                   'name':u'生病',
                   'type':self.env.ref('staff.holiday_type_1').id,
                   'staff_id':self.env.ref('staff.staff_1').id,
                   'date_start':'2016-05-02',
                   'date_end':'2016-05-04',
                    })
        holiday.onchange_days()
        holiday.date_end='2016-05-01'
        with self.assertRaises(except_orm):
            holiday.onchange_days()
        
   
