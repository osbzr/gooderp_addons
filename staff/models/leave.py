# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
import time
import datetime

# 请假单确认状态可选值
LEAVE_STATES = [
    ('draft', u'未确认'),
    ('done', u'已确认'), ]


class StaffLeave(models.Model):
    _name = 'staff.leave'
    _description = u'请假单'
    _inherit = ['mail.thread']

    @api.model
    def _set_staff_id(self):
        return self.env.uid

    name = fields.Text(string=u'请假缘由',
                       readonly=True,
                       states={'draft': [('readonly', False)]},
                       )
    user_id = fields.Many2one('res.users',
                              string=u'请假人',
                              default=_set_staff_id,
                              readonly=True,
                              states={'draft': [('readonly', False)]}
                              )
    date_start = fields.Datetime(string=u'离开时间',
                                 readonly=True,
                                 states={'draft': [('readonly', False)]}
                                 )
    date_stop = fields.Datetime(string=u'回来时间',
                                readonly=True,
                                states={'draft': [('readonly', False)]})
    leave_type = fields.Selection([('no_pay', u'无薪'), ('with_pay', u'带薪'),
                                   ('compensation_day', u'补偿日数'), ('sick_leave', u'病假')],
                                  required=True, string=u'准假类型', readonly=True,
                                  states={'draft': [('readonly', False)]})
    leave_dates = fields.Float(u'请假天数', readonly=True,
                               states={'draft': [('readonly', False)]})
    state = fields.Selection(LEAVE_STATES, u'状态', readonly=True,
                             help=u"请假单的状态", index=True, copy=False,
                             default='draft')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.one
    def leave_done(self):
        '''确认请假单'''
        if self.state == 'done':
            raise UserError(u'请不要重复确认！')
        self.state = 'done'

    @api.one
    def leave_draft(self):
        '''撤销确认请假单'''
        if self.state == 'draft':
            raise UserError(u'请不要重复撤销确认！')
        self.state = 'draft'

    @api.one
    @api.constrains('leave_dates')
    def check_leave_dates(self):
        if self.leave_dates <= 0:
            raise UserError(u'请假天数不能小于或等于零')
