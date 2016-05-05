# -*- coding: utf-8 -*-
from openerp import fields, models, api
from datetime import datetime
from openerp.exceptions import except_orm


class staff_holidays(models.Model):
    _name = 'staff.holidays'
    
    @api.one
    @api.onchange('date_start','date_end')
    def onchange_days(self):
        '''日期改变更新天数'''
        if self.date_start and self.date_end:
            date_start = datetime.strptime(self.date_start,'%Y-%m-%d')
            date_end = datetime.strptime(self.date_end,'%Y-%m-%d')
            holidays_days = (date_end - date_start).days + 1
            if holidays_days < 1:
                raise except_orm(u'错误', u'结束时间必须大于起始时间')
            else:
                self.days = holidays_days
    
    name = fields.Char(u'原因')
    type = fields.Many2one('core.value',u'类型',
                           domain=[('type','=','staff_holiday')],
                           context={'type':'staff_holiday'},required=True)
    state = fields.Selection([
                              ('draft',u'待审批'),
                              ('done',u'已审批')
                              ],u'状态',default='draft')
    staff_id = fields.Many2one('staff',u'员工',required=True)
    department_id = fields.Many2one('staff.department',u'部门')
    date_start = fields.Date(u'开始时间',required=True,default=datetime.now().strftime('%Y-%m-%d'))
    date_end = fields.Date(u'结束时间',required=True,default=datetime.now().strftime('%Y-%m-%d'))
    days = fields.Float(u'天数')







