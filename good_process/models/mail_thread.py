# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import  ValidationError

class mail_thread(models.AbstractModel):
    _inherit = 'mail.thread'
    _to_approver_ids = fields.One2many('good_process.approver',  'res_id',
        domain=lambda self: [('model', '=', self._name)], auto_join=True, string='待审批人')
    _approver_num = fields.Integer(string='总审批人数')

    def __get_groups__(self, process_rows):
        groups = []
        if process_rows:
            [groups.append((line.group_id, line.sequence)) for line in self.env['good_process.process_line'].search(
                [('process_id', '=', process_rows.id)], order='sequence')]
        return groups

    def __get_users__(self, groups):
        users = []
        for group, sequence in groups:
            [(users.append((user, sequence, group.id)))
             for user in group.users]
        return users

    def __get_user_manager__(self, thread_row, process_rows):
        return_vals = False
        if process_rows.is_department_approve:
            staff_row = self.env['staff'].search([('user_id', '=', thread_row.create_uid.id)])
            if staff_row and getattr(staff_row, 'parent_id', False):
                return_vals = staff_row.parent_id.user_id
        return return_vals

    def __add_approver__(self, thread_row, model_name):
        #TODO 加上当前用户的部门经理
        approver_rows = []
        users = []
        process_rows = self.env['good_process.process'].search(
            [('model_id.model', '=', model_name), ('type', '=', getattr(thread_row, 'type', False))])
        groups = self.__get_groups__(process_rows)
        department_manager = self.__get_user_manager__(thread_row, process_rows)
        if department_manager:
            users.append((department_manager, 0, False))
        users.extend(self.__get_users__(groups))
        [approver_rows.append(self.env['good_process.approver'].create(
            {'user_id': user.id,
             'res_id': thread_row.id,
             'sequence': sequence,
             'group_id': groud_id,
             'model': thread_row._name})) for user, sequence, groud_id in users]
        return [{'id': row.id, 'display_name': row.user_id.name} for row in approver_rows]


    def __good_approver_send_message__(self, active_id, active_model, message):
        mode_row = self.env[active_model].browse(active_id)
        user_row = self.env['res.users'].browse(self.env.uid)
        message_text = u"%s %s %s %s" % (user_row.name, message, mode_row._name, mode_row.name)
        mode_row.message_post(message_text, subtype='mail.mt_comment')

    def __is_departement_manager__(self, department_row):
        return_vals = department_row.id
        if department_row:
            department_row.unlink()
        return return_vals

    def __has_manager__(self, active_id, active_model):
        department_row = self.env['good_process.approver'].search([('model', '=', active_model),
                                                                   ('res_id', '=', active_id),
                                                                   ('sequence', '=', 0), ('group_id', '=', False)])
        return department_row

    @api.model
    def good_process_approve(self, active_id, active_model):
        return_vals = []
        manger_row = self.__has_manager__(active_id, active_model)
        model_row = self.env[active_model].browse(active_id)
        if (manger_row and manger_row.user_id.id == self.env.uid) or not manger_row:
            manger_user = []
            if manger_row:
                manger_user = [manger_row.user_id.id]
                return_vals.append(self.__is_departement_manager__(manger_row))
            users, can_clean_groups = (self.__get_user_group__(active_id, active_model, manger_user, model_row))
            return_vals.extend(self.__remove_approver__(active_id, active_model, users, can_clean_groups))
            if return_vals:
                self.__good_approver_send_message__(active_id, active_model, u'同意')
            else:
                return_vals = u'您不是这张单据的下一个审批者'
        else:
            return_vals = u'您不是这张单据的下一个审批者'
        return return_vals

    @api.model
    def good_process_refused(self, active_id, active_model):
        mode_row = self.env[active_model].browse(active_id)
        users, groups = self.__get_user_group__(active_id, active_model, [], mode_row)
        approver_rows = self.env['good_process.approver'].search([('model', '=', active_model),
                                                                  ('res_id', '=', active_id)])
        if mode_row._approver_num==len(mode_row._to_approver_ids):
            retturn_vals = u'您是第一批需要审批的人，无需拒绝！'
        elif approver_rows and users:
            approver_rows.unlink()
            self.__good_approver_send_message__(active_id, active_model, u'拒绝')
            retturn_vals = self.__add_approver__(mode_row, active_model)

        else:
            retturn_vals = u'已经通过不能拒绝！'
        return retturn_vals


    @api.model
    def create(self, vals):
        thread_row = super(mail_thread, self).create(vals)
        approvers = self.__add_approver__(thread_row, self._name)
        thread_row._approver_num = len(approvers)
        return thread_row
    
    @api.multi
    def write(self, vals):
        for th in self:
            if th._approver_num != len(th._to_approver_ids) and not vals.get('_approver_num'):
                raise ValidationError(u"审批中不可修改")
        thread_row = super(mail_thread, self).write(vals)
        return thread_row

    def __get_user_group__(self, active_id,  active_model, users, mode_row):
        all_groups = []
        process_rows = self.env['good_process.process'].search([('model_id.model', '=', active_model),
                                                                ('type', '=', getattr(mode_row, 'type', False))])
        line_rows = self.env['good_process.process_line'].search(
            [('process_id', '=', process_rows.id)], order='sequence')
        least_num = 'default_vals'
        for line in line_rows:
            approver_s = self.env['good_process.approver'].search([('model', '=', active_model),
                                                                   ('group_id', '=', line.group_id.id),
                                                                   ('res_id', '=', active_id)])

            if least_num == 'default_vals' and approver_s:
                least_num = line.sequence
            if least_num == line.sequence and self.env.uid in [user.id for user in line.group_id.users]:
                users = [self.env.uid]
            if not line.is_all_approve:
                all_groups.append(line.group_id)
        can_clean_groups = []
        for group in all_groups:
            all_group_user = [user.id for user in group.users]
            if len(list(set(all_group_user).difference(users)))!= len(all_group_user):
                can_clean_groups.append(group.id)
        return users, can_clean_groups

    def __get_remove_approver__(self, thread_row, user_ids, can_clean_groups):
        """
        去除审批人 - if 判断当前用户是否属于当前状态的审批人 里面
                        取得 当前用户在审批人里面的记录 （或者全组一人审批即可的 情况下  这个组里面其他人）
                    else:
                        判断 是否轮到当前用户审批 否则跳出循环

                    如果是全组审批并且取得一个审批人记录 就跳出循环

        :param thread_row:
        :param user_ids: 当前状态的审批人们
        :param is_all_approve:
        :param sequence:
        :return: 审批人 对应的记录
        """
        remove_approve, return_vals = [], []
        for approver in thread_row._to_approver_ids:
            if approver.user_id.id in user_ids or approver.group_id.id in can_clean_groups:
                remove_approve.append(approver)
                return_vals.append(approver.id)
        return return_vals, remove_approve

    @api.model
    def __remove_approver__(self, active_id, active_model, user_ids, can_clean_groups):
        return_vals = False
        if active_id:
            thread_row = self.env[active_model].browse(active_id)
            return_vals, remove_approvers = self.__get_remove_approver__(thread_row, user_ids, can_clean_groups)
            if remove_approvers:
                [approver.unlink() for approver in remove_approvers]
        return return_vals

class approver(models.Model):
    _name = 'good_process.approver'
    _rec_name = 'user_id'
    model = fields.Char('模型', index=True)
    res_id = fields.Integer('ID', index=True)
    group_id = fields.Many2one('res.groups', string='用户组')
    user_id = fields.Many2one('res.users', string='用户')
    sequence = fields.Integer(string='顺序')

    @api.model_cr
    def init(self):
        self._cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'good_process_approver_model_res_id_idx'""")
        if not self._cr.fetchone():
            self._cr.execute("""CREATE INDEX good_process_approver_model_res_id_idx ON good_process_approver (model, res_id)""")

class process(models.Model):
    _name = 'good_process.process'
    _rec_name = 'model_id'
    model_id = fields.Many2one('ir.model')
    type = fields.Char(u'类型', help=u'有些单据根据type字段区分具体流程')
    is_department_approve = fields.Boolean(string='部门经理审批')
    line_ids = fields.One2many('good_process.process_line', 'process_id', string='审批组')

class process_line(models.Model):
    _name = 'good_process.process_line'
    sequence = fields.Integer(string='序号')
    group_id = fields.Many2one('res.groups', string='审批组')
    is_all_approve = fields.Boolean(string='是否需要本组用户全部审批')
    process_id = fields.Many2one('good_process.process')