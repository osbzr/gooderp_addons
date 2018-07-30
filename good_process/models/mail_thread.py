# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class MailThread(models.AbstractModel):
    '''
    针对系统内的单据增加审批流程控制
    增加两个字段：_to_approver_ids 记录还有谁需要审批（用来判断审批是否结束）
                 _approver_num 整个流程涉及的审批者数量（用来判断审批是否开始）
    '''
    _inherit = 'mail.thread'

    @api.one
    @api.depends('_to_approver_ids', '_approver_num')
    def _get_approve_state(self):
        """计算审批状态"""
        to_approver = len(self._to_approver_ids)
        if not to_approver:
            self._approve_state = u'已审批'
        elif to_approver == self._approver_num:
            self._approve_state = u'已提交'
        else:
            self._approve_state = u'审批中'

    _to_approver_ids = fields.One2many('good_process.approver',  'res_id', readonly='1',
                                       domain=lambda self: [('model', '=', self._name)], auto_join=True, string='待审批人')
    _approver_num = fields.Integer(string='总审批人数')
    _approve_state = fields.Char(u'审批状态',
                                 compute='_get_approve_state')

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
        '''
        如此流程需要记录创建者的部门经理审批，取得部门经理用户
        '''
        return_vals = False
        if process_rows.is_department_approve:
            staff_row = self.env['staff'].search(
                [('user_id', '=', thread_row.create_uid.id)])
            if staff_row and getattr(staff_row, 'parent_id', False):
                return_vals = staff_row.parent_id.user_id
        return return_vals

    def __add_approver__(self, thread_row, model_name, active_id):
        # TODO 加上当前用户的部门经理
        approver_rows = []
        users = []
        process_rows = self.env['good_process.process'].search([('model_id.model', '=', model_name),
                                                                ('type', '=', getattr(thread_row, 'type', False))],
                                                               order='sequence')
        process_row = False
        for process in process_rows:
            domain = [('id', '=', active_id)]
            if process.applicable_domain:
                domain += safe_eval(process.applicable_domain)
            if self.env[model_name].search(domain):
                process_row = process
                break
        if not process_row:
            return []

        groups = self.__get_groups__(process_row)
        department_manager = self.__get_user_manager__(
            thread_row, process_row)
        if department_manager:
            users.append((department_manager, 0, False))
        users.extend(self.__get_users__(groups))
        [approver_rows.append(self.env['good_process.approver'].create(
            {'user_id': user.id,
             'res_id': thread_row.id,
             'model_type': thread_row._description,
             'record_name': getattr(thread_row, 'name', ''),
             'creator': thread_row.create_uid.id,
             'sequence': sequence,
             'group_id': groud_id,
             'model': thread_row._name})) for user, sequence, groud_id in users]
        return [{'id': row.id, 'display_name': row.user_id.name} for row in approver_rows]

    def __good_approver_send_message__(self, active_id, active_model, message):
        mode_row = self.env[active_model].browse(active_id)
        user_row = self.env['res.users'].browse(self.env.uid)
        message_text = u"%s %s %s %s" % (
            user_row.name, message, mode_row._name, mode_row.name)
        return message_text

    def __is_departement_manager__(self, department_row):
        return_vals = department_row.id
        if department_row:
            department_row.unlink()
        return return_vals

    def __has_manager__(self, active_id, active_model):
        department_row = self.env['good_process.approver'].search([('model', '=', active_model),
                                                                   ('res_id', '=',
                                                                    active_id),
                                                                   ('sequence', '=', 0), ('group_id', '=', False)])
        return department_row

    @api.model
    def good_process_approve(self, active_id, active_model):
        return_vals = []
        message = ''
        manger_row = self.__has_manager__(active_id, active_model)
        model_row = self.env[active_model].browse(active_id)
        if (manger_row and manger_row.user_id.id == self.env.uid) or not manger_row:
            manger_user = []
            if manger_row:
                manger_user = [manger_row.user_id.id]
                return_vals.append(self.__is_departement_manager__(manger_row))
            users, can_clean_groups = (self.__get_user_group__(
                active_id, active_model, manger_user, model_row))
            return_vals.extend(self.__remove_approver__(
                active_id, active_model, users, can_clean_groups))
            if return_vals:
                message = self.__good_approver_send_message__(
                    active_id, active_model, u'同意')
            else:
                return_vals = u'您不是这张单据的下一个审批者'
        else:
            return_vals = u'您不是这张单据的下一个审批者'
        return return_vals, message or ''

    @api.model
    def good_process_refused(self, active_id, active_model):
        message = ''
        mode_row = self.env[active_model].browse(active_id)
        users, groups = self.__get_user_group__(
            active_id, active_model, [], mode_row)
        approver_rows = self.env['good_process.approver'].search([('model', '=', active_model),
                                                                  ('res_id', '=', active_id)])
        if mode_row._approver_num == len(mode_row._to_approver_ids):
            return_vals = u'您是第一批需要审批的人，无需拒绝！'
        elif approver_rows and users:
            approver_rows.unlink()
            message = self.__good_approver_send_message__(
                active_id, active_model, u'拒绝')
            return_vals = self.__add_approver__(mode_row, active_model, active_id)

        else:
            return_vals = u'已经通过不能拒绝！'
        return return_vals, message or ''

    def is_current_model(self):
        """检查是否是当前对象"""
        action_id = self.env.context.get('params', False) \
                    and self.env.context['params'].get('action', False) \
                    or False
        if not action_id:
            return True
        current_model = self.env['ir.actions.act_window'].browse(action_id).res_model
        # 排除good_process.approver是因为从审批向导进去所有单据current_model != self._name导致跳过审批流程
        if current_model != self._name and current_model != 'good_process.approver':
            return False
        else:
            return True

    @api.model
    def create(self, vals):
        thread_row = super(MailThread, self).create(vals)
        approvers = self.__add_approver__(thread_row, self._name, thread_row.id)
        thread_row._approver_num = len(approvers)
        return thread_row

    @api.multi
    def write(self, vals):
        '''
        如果单据的审批流程已经开始（第一个人同意了才算开始） —— 至少一个审批人已经审批通过，不允许对此单据进行修改。
        '''
        if not self.is_current_model():
            return super(MailThread, self).write(vals)
        for th in self:
            ignore_fields = ['_approver_num',
                             '_to_approver_ids',
                             'message_ids',
                             'message_follower_ids',
                             'message_partner_ids',
                             'message_channel_ids',
                             'approve_uid',
                             'approve_date',
                             ]
            if any([vals.has_key(x) for x in ignore_fields]) or not th._approver_num:
                continue
            change_state = vals.get('state', False)

            if change_state == 'cancel':    # 作废时移除待审批人
                if not len(th._to_approver_ids) and th._approver_num:
                    raise ValidationError(u"已审批不可作废")
                if len(th._to_approver_ids) < th._approver_num:
                    raise ValidationError(u"审批中不可作废")
                for approver in th._to_approver_ids:
                    approver.unlink()
                return super(MailThread, self).write(vals)

            # 已提交，确认时报错
            if len(th._to_approver_ids) == th._approver_num and change_state == 'done':
                raise ValidationError(u"审批后才能确认")
            # 已审批
            if not len(th._to_approver_ids):
                if not change_state:
                    raise ValidationError(u'已审批不可修改')
                if change_state == 'draft':
                    vals.update({
                        '_approver_num': len(self.__add_approver__(th, th._name, th.id)),
                    })
            # 审批中，确认时报错，修改其他字段报错
            elif len(th._to_approver_ids) < th._approver_num:
                if change_state == 'done':
                    raise ValidationError(u"审批后才能确认")
                raise ValidationError(u"审批中不可修改")

        thread_row = super(MailThread, self).write(vals)
        return thread_row

    @api.multi
    def unlink(self):
        if not self.is_current_model():
            return super(MailThread, self).unlink()
        for th in self:
            if not len(th._to_approver_ids) and th._approver_num:
                raise ValidationError(u"已审批不可删除")
            if len(th._to_approver_ids) < th._approver_num:
                raise ValidationError(u"审批中不可删除")
            for Approver in th._to_approver_ids:
                Approver.unlink()
        return super(MailThread, self).unlink()

    def __get_user_group__(self, active_id,  active_model, users, mode_row):
        all_groups = []
        process_rows = self.env['good_process.process'].search([('model_id.model', '=', active_model),
                                                                ('type', '=', getattr(mode_row, 'type', False))],
                                                               order='sequence')
        process_row = False
        for process in process_rows:
            domain = [('id', '=', active_id)]
            if process.applicable_domain:
                domain += safe_eval(process.applicable_domain)
            if self.env[active_model].search(domain):
                process_row = process
                break
        if not process_row:
            return users, []

        line_rows = self.env['good_process.process_line'].search(
            [('process_id', '=', process_row.id)], order='sequence')
        least_num = 'default_vals'
        for line in line_rows:
            approver_s = self.env['good_process.approver'].search([('model', '=', active_model),
                                                                   ('group_id', '=',
                                                                    line.group_id.id),
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
            if len(list(set(all_group_user).difference(users))) != len(all_group_user):
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
        for Approver in thread_row._to_approver_ids:
            if Approver.user_id.id in user_ids or Approver.group_id.id in can_clean_groups:
                remove_approve.append(Approver)
                return_vals.append(Approver.id)
        return return_vals, remove_approve

    @api.model
    def __remove_approver__(self, active_id, active_model, user_ids, can_clean_groups):
        return_vals = False
        if active_id:
            thread_row = self.env[active_model].browse(active_id)
            return_vals, remove_approvers = self.__get_remove_approver__(
                thread_row, user_ids, can_clean_groups)
            if remove_approvers:
                [Approver.unlink() for Approver in remove_approvers]
        return return_vals


class Approver(models.Model):
    '''
    单据的待审批者
    '''
    _name = 'good_process.approver'
    _rec_name = 'user_id'
    _order = 'model, res_id, sequence'

    model_type = fields.Char(u'单据类型')
    record_name = fields.Char(u'编号')
    creator = fields.Many2one('res.users', u'申请人')
    model = fields.Char('模型', index=True)
    res_id = fields.Integer('ID', index=True)
    group_id = fields.Many2one('res.groups', string=u'审批组')
    group_name = fields.Char(related='group_id.name', string=u'名字')
    user_id = fields.Many2one('res.users', string=u'用户')
    sequence = fields.Integer(string=u'顺序')

    @api.multi
    def goto(self):
        self.ensure_one()
        views = self.env['ir.ui.view'].search(
            [('model', '=', self.model), ('type', '=', 'form')])
        model_obj = self.env[self.model]
        rec = model_obj.browse(self.res_id)
        if getattr(rec, 'is_return', False):
            for v in views:
                if '_return_' in v.xml_id:
                    vid = v.id
                    break
        else:
            vid = views[0].id

        return_vals = {
            'name': u'审批',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.model,
            'view_id': False,
            'views': [(vid, 'form')],
            'type': 'ir.actions.act_window',
            'res_id': self.res_id,
        }
        # 如果单据存在 type，根据type传回context
        if hasattr(model_obj, 'type'):
            rec_ctx = {}
            if rec.type == 'get':
                rec_ctx = {'default_get': 1}
            if rec.type == 'pay':
                rec_ctx = {'default_pay': 1}
            return_vals['context'] = rec_ctx
        return return_vals

    @api.model_cr
    def init(self):
        self._cr.execute(
            """SELECT indexname FROM pg_indexes WHERE indexname = 'good_process_approver_model_res_id_idx'""")
        if not self._cr.fetchone():
            self._cr.execute(
                """CREATE INDEX good_process_approver_model_res_id_idx ON good_process_approver (model, res_id)""")


class Process(models.Model):
    '''
    可供用户自定义的审批流程，可控制是否需部门经理审批。注意此规则只对修改之后新建（或被拒绝）的单据有效
    '''
    _name = 'good_process.process'
    _description = u'审批规则'
    _rec_name = 'model_id'
    model_id = fields.Many2one('ir.model', u'单据', required=True)
    type = fields.Char(u'类型', help=u'有些单据根据type字段区分具体流程')
    is_department_approve = fields.Boolean(string=u'部门经理审批')
    line_ids = fields.One2many(
        'good_process.process_line', 'process_id', string=u'审批组')
    active = fields.Boolean(u'启用', default=True)
    applicable_domain = fields.Char(u'适用条件')
    sequence = fields.Integer(u'优先级')

    @api.one
    @api.constrains('model_id', 'type', 'applicable_domain')
    def check_model_id(self):
        records = self.search([
            ('model_id', '=', self.model_id.id),
            ('type', '=', self.type),
            ('id', '!=', self.id),
            ('applicable_domain', '=', self.applicable_domain)])
        if records:
            raise ValidationError(u'审批规则必须唯一')

    @api.model
    def create(self, vals):
        """
        新建审批配置规则，如果配置的模型有type字段而规则未输入type，保存时给出提示
        """
        process_id = super(Process, self).create(vals)
        model = self.env[process_id.model_id.model]
        if hasattr(model, 'type') and not process_id.type:
            raise ValidationError(u'请输入类型')
        return process_id


class ProcessLine(models.Model):
    '''
    可控制由哪些审批组审批，各自的审批顺序是什么，组内用户都需要审还是一位代表审批即可
    '''
    _name = 'good_process.process_line'
    _description = u'审批规则行'
    _order = 'sequence'

    sequence = fields.Integer(string='序号')
    group_id = fields.Many2one('res.groups', string=u'审批组', required=True)
    is_all_approve = fields.Boolean(string=u'是否需要本组用户全部审批')
    process_id = fields.Many2one('good_process.process', u'审批规则', ondelete='cascade')
