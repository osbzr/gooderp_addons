# -*- coding: utf-8 -*-
from openerp import fields, models, api


class staff_contract(models.Model):
    _name='staff.contract'
    
    staff_id = fields.Many2one('staff',u'员工',required=True)
    
    over_date = fields.Date(u'到期日',required=True)
    basic_wage = fields.Float(u'基础工资')
    job_id = fields.Many2one('staff.job',u'岗位',required=True)