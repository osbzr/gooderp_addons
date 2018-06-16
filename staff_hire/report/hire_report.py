# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools
from odoo.addons.staff_hire.models import staff_hire


class staff_hire_report(models.Model):
    _name = "staff.hire.report"
    _description = u"招聘分析"
    _auto = False
    _rec_name = 'date_create'
    _order = 'date_create desc'

    active = fields.Boolean('Active')
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    date_create = fields.Datetime('Create Date', readonly=True)
    date_last_stage_update = fields.Datetime('Last Stage Update', readonly=True)
    job_id = fields.Many2one('staff.job', 'Applied Job', readonly=True)
    stage_id = fields.Many2one('staff.hire.stage', 'Stage')
    degree_id = fields.Many2one('core.value', 'Degree')
    department_id = fields.Many2one('staff.department', 'Department', readonly=True)
    priority = fields.Selection(staff_hire.AVAILABLE_PRIORITIES, 'Appreciation')
    salary_prop = fields.Float("Salary Proposed", digits=0)
    salary_prop_avg = fields.Float("Avg. Proposed Salary", group_operator="avg", digits=0)
    salary_exp = fields.Float("Salary Expected", digits=0)
    salary_exp_avg = fields.Float("Avg. Expected Salary", group_operator="avg", digits=0)
    delay_close = fields.Float('Avg. Delay to Close', digits=(16, 2), readonly=True, group_operator="avg", help="Number of Days to close the project issue")
    last_stage_id = fields.Many2one('staff.hire.stage', 'Last Stage')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'staff_hire_report')
        self._cr.execute("""
            create or replace view staff_hire_report as (
                 select
                     min(s.id) as id,
                     s.active,
                     s.create_date as date_create,
                     s.date_last_stage_update as date_last_stage_update,
                     s.company_id,
                     s.user_id,
                     s.job_id,
                     s.degree_id,
                     s.department_id,
                     s.priority,
                     s.stage_id,
                     s.last_stage_id,
                     sum(salary_proposed) as salary_prop,
                     (sum(salary_proposed)/count(*)) as salary_prop_avg,
                     sum(salary_expected) as salary_exp,
                     (sum(salary_expected)/count(*)) as salary_exp_avg,
                     extract('epoch' from (s.write_date-s.create_date))/(3600*24) as delay_close,
                     count(*) as nbr
                 from hire_applicant s
                 group by
                     s.active,
                     s.create_date,
                     s.write_date,
                     s.date_last_stage_update,
                     s.company_id,
                     s.user_id,
                     s.stage_id,
                     s.last_stage_id,
                     s.degree_id,
                     s.priority,
                     s.job_id,
                     s.department_id
            )
        """)
