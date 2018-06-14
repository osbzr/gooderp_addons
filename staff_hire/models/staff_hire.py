# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, SUPERUSER_ID
from odoo.exceptions import UserError


AVAILABLE_PRIORITIES = [
    ('0', u'一般'),
    ('1', u'良好'),
    ('2', u'优秀'),
    ('3', u'杰出')
]


class staff_hire_stage(models.Model):
    _name = "staff.hire.stage"
    _description = u"招聘阶段"
    _order = 'sequence'

    name = fields.Char(u"阶段名", required=True)
    sequence = fields.Integer(
        u"序号", default=10,
        help=u"按顺序显示列表中的各阶段。")
    job_id = fields.Many2one('staff.job', string=u'具体职位',
                             ondelete='cascade',
                             help=u'使用此阶段的具体职位。其他职位将不使用此阶段。')
    requirements = fields.Text(u"要求")
    template_id = fields.Many2one(
        'mail.template', u"使用模板",
        help=u"如果设置,当应聘者设置此场景时,将通过这个模板推送消息给相关应聘者")
    fold = fields.Boolean(
        u"在招聘管道收起",
        help=u"当这个阶段中没有任何记录要呈现的时候，这个阶段在看板视图中被折叠起来")


class hire_applicant(models.Model):
    _name = "hire.applicant"
    _description = u"招聘"
    _order = "priority desc, id desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'partner_name'

    def _default_stage_id(self):
        '''返回阶段的默认值'''
        ids = self.env['staff.hire.stage'].search([
            '|',
            ('job_id', '=', False),
            ('job_id', '=', self.job_id.id),
            ('fold', '=', False),
        ], order='sequence asc', limit=1).ids
        if ids:
            return ids[0]
        return False

    active = fields.Boolean(u"有效", default=True, help=u"如果“有效”字段设为false，它对信息进行隐藏但不删除它。")
    note = fields.Text(u"备注")
    email_from = fields.Char(u"Email", size=128, help=u"这些人将收到电子邮件")
    stage_id = fields.Many2one('staff.hire.stage', u'阶段', track_visibility='onchange',
                               domain="['|', ('job_id', '=', False), ('job_id', '=', job_id)]",
                               copy=False, index=True,
                               group_expand='_read_group_stage_ids',
                               default=_default_stage_id)
    last_stage_id = fields.Many2one('staff.hire.stage', u"最终阶段",
                                    help=u"当前阶段前的申请人阶段，用于招聘失败分析。")
    categ_ids = fields.Many2many('core.value', string=u"标签",
                                 domain=[('type', '=', 'hire_categ')],
                                 context={'type': 'hire_categ'}
                                 )
    company_id = fields.Many2one('res.company', u"公司", default=lambda self: self.env['res.company']._company_default_get())
    user_id = fields.Many2one('res.users', u"负责人", track_visibility="onchange", default=lambda self: self.env.uid)
    date_last_stage_update = fields.Datetime(u"最终阶段更新时间", index=True, default=fields.Datetime.now)
    date_action = fields.Date(u"下步计划日期")
    title_action = fields.Char(u"下步计划", size=64)
    priority = fields.Selection(AVAILABLE_PRIORITIES, u"欢迎度", default='0')
    job_id = fields.Many2one('staff.job', u"应聘职位", required=True)
    salary_proposed_extra = fields.Char(u"建议额外福利", help=u"除了建议薪资以外的福利待遇")
    salary_expected_extra = fields.Char(u"期望额外福利", help=u"除了期望薪资以外的福利待遇")
    salary_proposed = fields.Float(u"建议薪资", help=u"该公司的提议薪酬")
    salary_expected = fields.Float(u"期望薪资", help=u"申请人要求的薪酬")
    date_available = fields.Date(u"开始工作日期", help=u"申请人能够开始工作的日期")
    partner_name = fields.Char(u"应聘者姓名", required=True)
    partner_mobile = fields.Char(u"手机", size=32, required=True)
    degree_id = fields.Many2one('core.value', u"学历",
                              domain=[('type', '=', 'hire_degree')],
                              context={'type': 'hire_degree'}
                              )
    department_id = fields.Many2one('staff.department', u"部门")
    reference = fields.Char(u"推荐人")
    color = fields.Integer("Color Index", default=0)
    staff_id = fields.Many2one('staff', string=u"员工", track_visibility="onchange", help=u"关联员工")
    staff_name = fields.Char(related='staff_id.name', string=u"员工姓名")
    user_email = fields.Char(related='user_id.email', type="char", string=u"用户Email", readonly=True)
    attachment_number = fields.Integer(compute='_get_attachment_number', string=u"附件数量")
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'hire.applicant')], string=u'附件')
    source_id = fields.Many2one('core.value', u"来源", ondelete='restrict',
                                domain=[('type', '=', 'hire_source')],
                                context={'type': 'hire_source'}
                                )

    @api.multi
    def _get_attachment_number(self):
        '''计算简历个数'''
        read_group_res = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'hire.applicant'), ('res_id', 'in', self.ids)],
            ['res_id'], ['res_id'])
        attach_data = dict((res['res_id'], res['res_id_count']) for res in read_group_res)
        for record in self:
            record.attachment_number = attach_data.get(record.id, 0)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        '''看板视图上显示所有阶段（即使该阶段没有招聘记录）'''
        search_domain = [('job_id', '=', False)]
        if stages:
            search_domain = ['|', ('id', 'in', stages.ids)] + search_domain

        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    @api.onchange('job_id')
    def onchange_job_id(self):
        '''选择职位，带出部门、负责人及阶段'''
        vals = self._onchange_job_id_internal(self.job_id.id)
        self.department_id = vals['value']['department_id']
        self.user_id = vals['value']['user_id']
        self.stage_id = vals['value']['stage_id']

    def _onchange_job_id_internal(self, job_id):
        '''选择职位具体实现'''
        department_id = False
        user_id = False
        stage_id = self.stage_id.id
        if job_id:
            job = self.env['staff.job'].browse(job_id)
            department_id = job.department_id.id
            user_id = job.user_id.id
            if not self.stage_id:
                stage_ids = self.env['staff.hire.stage'].search([
                    '|',
                    ('job_id', '=', False),
                    ('job_id', '=', job.id),
                    ('fold', '=', False)
                ], order='sequence asc', limit=1).ids
                stage_id = stage_ids[0] if stage_ids else False

        return {'value': {
            'department_id': department_id,
            'user_id': user_id,
            'stage_id': stage_id
        }}

    @api.multi
    def write(self, vals):
        # stage_id: track last stage before update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
            for applicant in self:
                vals['last_stage_id'] = applicant.stage_id.id
                res = super(hire_applicant, self).write(vals)
        else:
            res = super(hire_applicant, self).write(vals)
        return res

    @api.multi
    def action_get_created_employee(self):
        """跳到新创建的员工界面"""
        self.ensure_one()
        action = self.env['ir.actions.act_window'].for_xml_id('staff', 'staff_action')
        action['res_id'] = self.mapped('staff_id').ids[0]
        action['domain'] = str([('id', '=', self.mapped('staff_id').ids[0])])
        return action

    @api.multi
    def action_makeMeeting(self):
        """ 打开会议的日历视图来安排当前申请人的会议"""
        self.ensure_one()
        partners = self.user_id.partner_id | self.department_id.manager_id.user_id.partner_id

        category = self.env.ref('staff_hire.categ_meet_interview')
        res = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
        res['context'] = {
            'default_partner_ids': partners.ids,
            'default_user_id': self.env.uid,
            'default_categ_ids': category and [category.id] or False,
        }
        return res


    @api.multi
    def action_get_attachment_tree_view(self):
        '''查看简历'''
        attachment_action = self.env.ref('base.action_attachment')
        action = attachment_action.read()[0]
        action['context'] = {'default_res_model': self._name, 'default_res_id': self.ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', self.ids)])
        action['search_view_id'] = (self.env.ref('staff_hire.ir_attachment_view_search_inherit_staff_hire').id, )
        return action

    @api.multi
    def _track_subtype(self, init_values):
        '''员工或阶段变更时消息作相应更新'''
        record = self[0]
        if 'staff_id' in init_values and record.staff_id:
            return 'staff_hire.mt_applicant_hired'
        elif 'stage_id' in init_values and record.stage_id and record.stage_id.sequence <= 1:
            return 'staff_hire.mt_applicant_new'
        elif 'stage_id' in init_values and record.stage_id and record.stage_id.sequence > 1:
            return 'staff_hire.mt_applicant_stage_changed'
        return super(hire_applicant, self)._track_subtype(init_values)

    @api.multi
    def create_employee_from_applicant(self):
        """ 创建员工 """
        staff = False
        for applicant in self:
            if not applicant.salary_proposed:
                raise UserError(u'请输入建议薪资')
            applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1})
            staff = self.env['staff'].create({'name': applicant.partner_name,
                                           'job_id': applicant.job_id.id,
                                           'department_id': applicant.department_id.id or False,
                                           'work_email': applicant.department_id and applicant.department_id.company_id and applicant.department_id.company_id.email or False,
                                           'work_phone': applicant.department_id and applicant.department_id.company_id and applicant.department_id.company_id.phone or False,
                                           'work_mobile': applicant.partner_mobile or False,
                                              })
            vals_contract = {
                'staff_id': staff.id,
                'basic_wage': applicant.salary_proposed,
                'job_id': applicant.job_id.id,
                'over_date': fields.date.today(),
            }
            contract = staff.contract_ids.create(vals_contract)
            contract.onchange_basic_wage()
            applicant.write({'staff_id': staff.id})
            # staff._broadcast_welcome()

        staff_action = self.env.ref('staff.staff_action')
        dict_act_window = staff_action.read([])[0]
        if staff:
            dict_act_window['res_id'] = staff.id
        dict_act_window['view_mode'] = 'form,tree'
        return dict_act_window

    @api.multi
    def archive_applicant(self):
        """拒绝"""
        for record in self:
            if record.active == False:
                raise UserError(u'请不要重复拒绝')
            record.write({'active': False})

    @api.multi
    def reset_applicant(self):
        """重新打开招聘"""
        for record in self:
            if record.active == True:
                raise UserError(u'请不要重复重新打开招聘')
            default_stage_id = self._default_stage_id()
            record.write({'active': True, 'stage_id': default_stage_id})
