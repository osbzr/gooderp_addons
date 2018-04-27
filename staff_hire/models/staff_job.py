# -*- coding: utf-8 -*-
from odoo import api, fields, models


class staff_job(models.Model):
    _name = "staff.job"
    _inherit = ["staff.job"]

    @api.model
    def _default_address_id(self):
        return self.env.user.company_id.partner_id

    address_id = fields.Many2one(
        'res.partner', "Job Location", default=_default_address_id,
        help="Address where employees are working")
    application_ids = fields.One2many('hr.applicant', 'job_id', "Applications")
    application_count = fields.Integer(compute='_compute_application_count', string="Applications")
    manager_id = fields.Many2one(
        'staff', related='department_id.manager_id', string="Department Manager",
        readonly=True, store=True)
    user_id = fields.Many2one('res.users', "Recruitment Responsible", track_visibility='onchange')
    document_ids = fields.One2many('ir.attachment', compute='_compute_document_ids', string="Applications")
    documents_count = fields.Integer(compute='_compute_document_ids', string="Documents")
    # alias_id = fields.Many2one(
    #     'mail.alias', "Alias", ondelete="restrict", required=True,
    #     help="Email alias for this job position. New emails will automatically create new applicants for this job position.")

    # expected_employees = fields.Integer(compute='_compute_employees', string='Total Forecasted Employees', store=True,
    #                                     help='Expected number of employees for this job position after new recruitment.')
    # no_of_employee = fields.Integer(compute='_compute_employees', string="Current Number of Employees", store=True,
    #                                 help='Number of employees currently occupying this job position.')
    no_of_recruitment = fields.Integer(string='Expected New Employees', copy=False,
                                       help='Number of new employees you expect to recruit.', default=1)
    no_of_hired_employee = fields.Integer(string='Hired Employees', copy=False,
                                          help='Number of hired employees for this job position during recruitment phase.')
    color = fields.Integer("Color Index")
    state = fields.Selection([
        ('recruit', '招聘中'),
        ('open', '不招聘')
    ], string=u'状态', readonly=True, required=True, track_visibility='always', copy=False, default='recruit',
        help="Set whether the recruitment process is open or closed for this job position.")

    def _compute_document_ids(self):
        applicants = self.mapped('application_ids').filtered(lambda self: not self.emp_id)
        app_to_job = dict((applicant.id, applicant.job_id.id) for applicant in applicants)
        attachments = self.env['ir.attachment'].search([
            '|',
            '&', ('res_model', '=', 'staff.job'), ('res_id', 'in', self.ids),
            '&', ('res_model', '=', 'hr.applicant'), ('res_id', 'in', applicants.ids)])
        result = dict.fromkeys(self.ids, self.env['ir.attachment'])
        for attachment in attachments:
            if attachment.res_model == 'hr.applicant':
                result[app_to_job[attachment.res_id]] |= attachment
            else:
                result[attachment.res_id] |= attachment

        for job in self:
            job.document_ids = result[job.id]
            job.documents_count = len(job.document_ids)

    @api.multi
    def _compute_application_count(self):
        read_group_result = self.env['hr.applicant'].read_group([('job_id', '=', self.id)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in read_group_result)
        for job in self:
            job.application_count = result.get(job.id, 0)

    @api.model
    def create(self, vals):
        return super(staff_job, self.with_context(mail_create_nolog=True)).create(vals)

    @api.multi
    def action_set_no_of_recruitment(self, value):
        return self.write({'no_of_recruitment': value})

    @api.multi
    def set_open(self):
        return self.write({
            'state': 'open',
            'no_of_recruitment': 0,
            'no_of_hired_employee': 0
        })