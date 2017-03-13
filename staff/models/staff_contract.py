# -*- coding: utf-8 -*-
from odoo import fields, models, api


class staff_contract(models.Model):
    _name = 'staff.contract'
    _description = u'员工合同'

    staff_id = fields.Many2one('staff', u'员工', required=True)

    over_date = fields.Date(u'到期日', required=True)
    basic_wage = fields.Float(u'基础工资')
    endowment = fields.Float(u'个人养老保险')
    health = fields.Float(u'个人医疗保险')
    unemployment = fields.Float(u'个人失业保险')
    housing_fund = fields.Float(u'个人住房公积金')
    job_id = fields.Many2one('staff.job', u'岗位', required=True)
