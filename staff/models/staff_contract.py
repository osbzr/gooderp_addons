# -*- coding: utf-8 -*-
from odoo import fields, models, api


class StaffContract(models.Model):
    _name = 'staff.contract'
    _description = u'员工合同'

    staff_id = fields.Many2one('staff', u'员工', required=True)

    over_date = fields.Date(u'到期日', required=True)
    basic_wage = fields.Float(u'基础工资')
    endowment = fields.Float(u'个人养老保险')
    health = fields.Float(u'个人医疗保险')
    unemployment = fields.Float(u'个人失业保险')
    housing_fund = fields.Float(u'个人住房公积金')
    endowment_co = fields.Float(u'公司养老保险',
                                help=u'公司承担的养老保险')
    health_co = fields.Float(u'公司医疗保险',
                             help=u'公司承担的医疗保险')
    unemployment_co = fields.Float(u'公司失业保险',
                                   help=u'公司承担的失业保险')
    injury = fields.Float(u'公司工伤保险',
                          help=u'公司承担的工伤保险')
    maternity = fields.Float(u'公司生育保险',
                             help=u'公司承担的生育保险')
    housing_fund_co = fields.Float(u'公司住房公积金',
                                   help=u'公司承担的住房公积金')
    job_id = fields.Many2one('staff.job', u'岗位', required=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
