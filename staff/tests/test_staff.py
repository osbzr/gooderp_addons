# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm, ValidationError


class test_staff(TransactionCase):
    
    def test_get_image(self):
        '''拿到用户头像,职位的onchange'''
        staff_pro = self.env['staff'].create({
                                              'name':'DemoUser',
                                              'user_id':1,
                                              'job_id':self.env.ref('staff.staff_job_1').id})
        staff_pro._get_image()
        staff_pro.onchange_job_id()

        
   
