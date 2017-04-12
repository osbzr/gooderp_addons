# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import  ValidationError

class mail_thread(models.AbstractModel):
    _inherit = 'mail.thread'
    _to_approver_ids = fields.One2many('good_process.approver',  'res_id',
        domain=lambda self: [('model', '=', self._name)], auto_join=True, string='待审批人')

    def get_groups(self, model_name):
        process_rows = self.env['good_process.process'].search([('model_id.model', '=', model_name)])
        groups = []
        if process_rows:
            [groups.append((line.group_id, line.sequence)) for line in self.env['good_process.process_line'].search(
                [('process_id', '=', process_rows.id)], order='sequence')]
        return groups

    def get_users(self, groups):
        users = []
        sequence_dict = {}
        for group, sequence in groups:
            [(users.append(user),sequence_dict.update({user.id:sequence}))
             for user in group.users]

        return users, sequence_dict

    def _add_approver(self, thread_row, model_name):

        groups = self.get_groups(model_name)
        users, user_sequence_dict= self.get_users(groups)
        approver_rows = []
        [approver_rows.append(self.env['good_process.approver'].create(
            {'user_id': user.id,
             'res_id': thread_row.id,
             'sequence': user_sequence_dict.get(user.id),
             'model': thread_row._name})) for user in users]
        return [{'id': row.id, 'display_name': row.user_id.name} for row in approver_rows]

    # def constract_message(self, name, group):
    #     message = ""
    #     user_row = self.env['res.users'].browse(self.env.uid)
    #     for group in user_row.group_ids:
    #         if group.category_id.name == 'Gooderp':
    #             message = "%s %s %s" % (name, group.name, user_row.name)
    #     return message

    def good_approver_send_message(self, active_id, active_model, group, message):
        mode_row = self.env[active_model].browse(active_id)
        user_row = self.env['res.users'].browse(self.env.uid)
        message_text = u"%s %s %s %s" % (group.name, user_row.name, message, mode_row.name)
        mode_row.message_post(message_text, subtype='mail.mt_comment')

    @api.model
    def approve(self, active_id, active_model):
        group, user_ids, is_all_approve, sequence = self.get_user_group(active_model)
        return_vals = self._remove_approver(active_id, active_model, user_ids, is_all_approve, sequence)
        if return_vals:
            self.good_approver_send_message(active_id, active_model, group, u'同意')
        else:
            return_vals = u'这个单子您还没必要审批！'
        return return_vals

    @api.model
    def refused(self, active_id, active_model):
        group, user_ids, is_all_approve, sequence = self.get_user_group(active_model)
        mode_row = self.env[active_model].browse(active_id)
        approver_rows = self.env['good_process.approver'].search([('model', '=', active_model),
                                                                  ('res_id', '=', active_id)])
        if approver_rows:
            approver_rows.unlink()
            self.good_approver_send_message(active_id, active_model, group, u'拒绝')
            retturn_vals = self._add_approver(mode_row, active_model)
        else:
            retturn_vals = u'已经通过能拒绝！'
        return retturn_vals


    @api.model
    def create(self, vals):
        thread_row = super(mail_thread, self).create(vals)
        self._add_approver(thread_row, self._name)
        return thread_row

    def get_user_group(self, active_model):
        process_rows = self.env['good_process.process'].search([('model_id.model', '=', active_model)])
        group_dict = {}
        [group_dict.update({line.group_id.id: (line.is_all_approve, line.sequence)})
         for line in self.env['good_process.process_line'].search(
            [('process_id', '=', process_rows.id)], order='sequence')]
        group = self.env['res.groups'].search([('id', 'in', group_dict.keys()),
                                               ('users', 'in', self.env.uid)])
        return (group, [user.id for user in group.users],
                group_dict.get(group.id, [False, 0])[0], group_dict.get(group.id, [False,0])[1])

    def get_remove_approver(self, thread_row, user_ids, is_all_approve, sequence):
        remove_approve, return_vals = [], []
        group_id = False
        for approver in thread_row._to_approver_ids:
            if approver.user_id.id in user_ids:
                if approver.user_id.id == self.env.uid or group_id == approver.group_id.id:
                    remove_approve.append(approver)
                    return_vals.append(approver.id)
                    group_id = approver.group_id.id
            elif approver.sequence != sequence and not return_vals:
                break
            if return_vals and is_all_approve:
                break
        return return_vals, remove_approve

    @api.model
    def _remove_approver(self, active_id, active_model, user_ids, is_all_approve, sequence):
        return_vals = False
        if active_id:
            thread_row = self.env[active_model].browse(active_id)
            return_vals, remove_approvers = self.get_remove_approver(thread_row,
                                                                     user_ids, is_all_approve, sequence)
            if remove_approvers:
                [approver.unlink() for approver in remove_approvers]
        return return_vals

class approver(models.Model):
    _name = 'good_process.approver'
    _rec_name = 'user_id'
    _order = 'sequence'
    model = fields.Char('Related Document Model', index=True)
    res_id = fields.Many2one('Related Document ID', index=True)
    group_id = fields.Many2one('res.groups', string='用户组')
    user_id = fields.Many2one('res.users', string='用户')
    sequence = fields.Integer(string='顺序')
    _approver_num = fields.Integer(string='总审批人数')

    @api.model_cr
    def init(self):
        self._cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'good_process_approver_model_res_id_idx'""")
        if not self._cr.fetchone():
            self._cr.execute("""CREATE INDEX good_process_approver_model_res_id_idx ON good_process_approver (model, res_id)""")

class process(models.Model):
    _name = 'good_process.process'
    _rec_name = 'model_id'
    model_id = fields.Many2one('ir.model')
    is_department_approve = fields.Boolean(string='部门经理审批')
    line_ids = fields.One2many('good_process.process_line', 'process_id', string='审批组')

class process_line(models.Model):
    _name = 'good_process.process_line'
    sequence = fields.Integer(string='序号')
    group_id = fields.Many2one('res.groups', string='序号')
    is_all_approve = fields.Boolean(string='是否全部审批')
    process_id = fields.Many2one('process')