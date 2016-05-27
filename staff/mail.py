# -*- coding: utf-8-*- 

from openerp import models
from openerp.osv import osv, fields
from datetime import datetime
 
class mail_message(osv.Model):
 
    _inherit = 'mail.message'
 
    def staff_birthday_message(self, cr, uid, context = None):
        values = {}
        newid = -1
        staff_obj = self.pool.get("staff")
        staff_ids = staff_obj.search(cr, uid, [], context = context)
         
        for staff in staff_obj.browse(cr, uid, staff_ids, context=context):
            if not staff.birthday:
                return
            #获取当前月日     和    员工生日
            now = datetime.now().strftime("%m-%d")
            staff_bir = staff.birthday[5:]
            if now == staff_bir:
                #创建一条祝福信息
                values['subject'] = "生日快乐！"
                values['model'] = "mail.group"
                values['body'] = staff.name + "，祝你生日快乐!"
                values['res_id'] = 1
                newid = self.create(cr, uid, values, context) 
        return newid
