# -*- coding: utf-8 -*-

from odoo import api, fields, models
import time,datetime

class staff_leave(models.Model):
    _name = 'staff.leave'

    @api.model
    def _set_staff_id(self):
        return self.env.uid

    name = fields.Text(string=u'请假缘由')
    user_id = fields.Many2one('res.users', string=u'请假人', default=_set_staff_id)
    date_start = fields.Datetime(string=u'离开时间')
    date_stop = fields.Datetime(string=u'回来时间')
    leave_type = fields.Selection([('no_pay', u'无薪'),('with_pay', u'带薪'),
                                   ('compensation_day', u'补偿日数'),('sick_leave', u'病假')],
                                    default='no_pay', string=u'准假类型')
    leave_dates = fields.Integer(u'请假时长', compute='onchange_data_start_or_stop', default=1)

    @api.one
    @api.depends('date_start','date_stop')
    def onchange_data_start_or_stop(self):
        if self.date_start and self.date_stop:
            date_start_struct = time.strptime(self.date_start, "%Y-%m-%d %H:%M:%S")  # 字符串转换成time类型
            date_stop_struct = time.strptime(self.date_stop, "%Y-%m-%d %H:%M:%S")  # 字符串转换成time类型
            date_start = datetime.datetime(date_start_struct[0], date_start_struct[1], date_start_struct[2])
            date_stop = datetime.datetime(date_stop_struct[0], date_stop_struct[1], date_stop_struct[2])
            self.leave_dates = (date_stop - date_start).days or 1
