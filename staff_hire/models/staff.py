# -*- coding: utf-8 -*-

from odoo import api, fields, models


class staff(models.Model):
    _inherit = "staff"

    newly_hired_staff = fields.Boolean(u'新进员工', compute='_compute_newly_hired_staff',
                                          search='_search_newly_hired_staff')

    @api.multi
    def _compute_newly_hired_staff(self):
        '''计算新进员工数'''
        read_group_result = self.env['hire.applicant'].read_group(
            [('staff_id', 'in', self.ids), ('job_id.state', '=', 'open')],
            ['staff_id'], ['staff_id'])
        result = dict((data['staff_id'], data['staff_id_count'] > 0) for data in read_group_result)

        for record in self:
            # record.newly_hired_staff = result.get(record.id, False)
            for key, value in result.iteritems():
                if record.id in key:
                    record.newly_hired_staff = True

    def _search_newly_hired_staff(self, operator, value):
        applicants = self.env['hire.applicant'].search([('job_id.state', '=', 'open')])
        return [('id', 'in', applicants.ids)]

    # @api.multi
    # def _broadcast_welcome(self):
    #     """ Broadcast the welcome message to all users in the employee company. """
    #     self.ensure_one()
    #     IrModelData = self.env['ir.model.data']
    #     channel_all_employees = IrModelData.xmlid_to_object('mail.channel_all_employees')
    #     template_new_employee = IrModelData.xmlid_to_object('hr_recruitment.email_template_data_applicant_employee')
    #     if template_new_employee:
    #         MailTemplate = self.env['mail.template']
    #         body_html = MailTemplate.render_template(template_new_employee.body_html, 'hr.employee', self.id)
    #         subject = MailTemplate.render_template(template_new_employee.subject, 'hr.employee', self.id)
    #         channel_all_employees.message_post(
    #             body=body_html, subject=subject,
    #             subtype='mail.mt_comment')
    #     return True