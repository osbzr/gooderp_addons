# -*- coding: utf-8 -*-
from odoo import api, fields, models


class staff_job(models.Model):
    _name = "staff.job"
    _inherit = ["staff.job"]

    @api.model
    def _default_address_id(self):
        print 'ppppppp',self.env.user.company_id,self.env.user.company_id.name
        return self.env.user.company_id

    address_id = fields.Many2one(
        'partner', "Job Location", default=_default_address_id,
        help="Address where employees are working")
    application_ids = fields.One2many('hr.applicant', 'job_id', "Applications")
    application_count = fields.Integer(compute='_compute_application_count', string="Applications")
    manager_id = fields.Many2one(
        'staff', related='department_id.manager_id', string=u"部门经理",
        readonly=True, store=True)
    user_id = fields.Many2one('res.users', u"招聘负责人", track_visibility='onchange')
    document_ids = fields.One2many('ir.attachment', compute='_compute_document_ids', string=u"简历")
    documents_count = fields.Integer(compute='_compute_document_ids', string=u"简历数")
    # alias_id = fields.Many2one(
    #     'mail.alias', "Alias", ondelete="restrict", required=True,
    #     help="Email alias for this job position. New emails will automatically create new applicants for this job position.")

    expected_employees = fields.Integer(compute='_compute_employees', string=u'预计总数', store=True,
                                        help=u'招聘新员工后，预计该职位的员工人数。')
    no_of_employee = fields.Integer(compute='_compute_employees', string=u"当前员工数", store=True,
                                    help=u'该职位当前员工数量')
    no_of_recruitment = fields.Integer(string=u'预计新员工数', copy=False,
                                       help=u'期望招聘的新员工数量', default=1)
    no_of_hired_employee = fields.Integer(string=u'招到员工数', copy=False,
                                          help=u'在招聘阶段聘用的员工数量')
    staff_ids = fields.One2many('staff', 'job_id', string='Employees', groups='base.group_user')

    color = fields.Integer("Color Index")
    state = fields.Selection([
        ('recruit', u'招聘中'),
        ('open', u'不招聘')
    ], string=u'状态', readonly=True, required=True, track_visibility='always', copy=False, default='recruit',
        help="Set whether the recruitment process is open or closed for this job position.")

    @api.depends('no_of_recruitment', 'staff_ids.job_id', 'staff_ids.active')
    def _compute_employees(self):
        employee_data = self.env['staff'].read_group([('job_id', 'in', self.ids)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in employee_data)
        for job in self:
            job.no_of_employee = result.get(job.id, 0)
            job.expected_employees = result.get(job.id, 0) + job.no_of_recruitment

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
    def action_get_attachment_tree_view(self):
        action = self.env.ref('base.action_attachment').read()[0]
        action['context'] = {
            'default_res_model': self._name,
            'default_res_id': self.ids[0]
        }
        action['search_view_id'] = (self.env.ref('staff_hire.ir_attachment_view_search_inherit_hr_recruitment').id,)
        action['domain'] = ['|', '&', ('res_model', '=', 'hr.job'), ('res_id', 'in', self.ids), '&',
                            ('res_model', '=', 'hr.applicant'), ('res_id', 'in', self.mapped('application_ids').ids)]
        return action

    @api.multi
    def action_set_no_of_recruitment(self, value):
        return self.write({'no_of_recruitment': value})

    @api.multi
    def set_recruit(self):
        for record in self:
            no_of_recruitment = 1 if record.no_of_recruitment == 0 else record.no_of_recruitment
            record.write({'state': 'recruit', 'no_of_recruitment': no_of_recruitment})
        return True

    @api.multi
    def set_open(self):
        return self.write({
            'state': 'open',
            'no_of_recruitment': 0,
            'no_of_hired_employee': 0
        })
