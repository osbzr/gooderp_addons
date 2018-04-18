# -*- coding: utf-8 -*-
from odoo import fields, models, api, tools, modules
from datetime import datetime
from odoo.exceptions import UserError
import re


class StaffDepartment(models.Model):
    _name = "staff.department"
    _description = u'员工部门'
    _inherits = {'auxiliary.financing': 'auxiliary_id'}

    auxiliary_id = fields.Many2one(
        string=u'辅助核算',
        comodel_name='auxiliary.financing',
        ondelete='cascade',
        required=True,
    )
    manager_id = fields.Many2one('staff', u'部门经理')
    member_ids = fields.One2many('staff', 'department_id', u'部门成员')
    parent_id = fields.Many2one('staff.department', u'上级部门')
    child_ids = fields.One2many('staff.department', 'parent_id', u'下级部门')
    jobs_ids = fields.One2many('staff.job', 'department_id', u'职位')
    note = fields.Text(u'备注')
    active = fields.Boolean(u'启用', default=True)

    @api.one
    @api.constrains('parent_id')
    def _check_parent_id(self):
        '''上级部门不能选择自己和下级的部门'''
        if self.parent_id:
            staffs = self.env['staff.department'].search(
                [('parent_id', '=', self.id)])
            if self.parent_id in staffs:
                raise UserError(u'上级部门不能选择他自己或者他的下级部门')

    @api.multi
    def view_detail(self):
        for child_department in self:
            context = {'default_name': child_department.name,
                       'default_manager_id': child_department.manager_id.id,
                       'default_parent_id': child_department.parent_id.id}
            res_id = self.env['staff.department'].search(
                [('id', '=', child_department.id)])
            view_id = self.env.ref('staff.view_staff_department_form').id

            return {
                'name': u'部门/' + child_department.name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'staff.department',
                'res_id': res_id.id,
                'view_id': False,
                'views': [(view_id, 'form')],
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'current',
            }


class StaffJob(models.Model):
    _name = "staff.job"
    _description = u'员工职位'

    name = fields.Char(u'职位', required=True)
    note = fields.Text(u'描述')
    account_id = fields.Many2one('finance.account', u'计提工资科目')
    department_id = fields.Many2one('staff.department', u'部门')
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    _sql_constraints = [
        ('name_uniq', 'unique(name,department_id)', '同部门的职位不能重复！')
    ]


class StaffEmployeeCategory(models.Model):
    _name = "staff.employee.category"
    _description = u'员工层级'

    name = fields.Char(u'名称',required=True)
    parent_id = fields.Many2one('staff.employee.category', u'上级标签', index=True)
    chield_ids = fields.One2many(
        'staff.employee.category', 'parent_id', u'下级标签')
    employee_ids = fields.Many2many('staff',
                                    'employee_category_rel',
                                    'category_id',
                                    'emp_id', u'员工')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())


class Staff(models.Model):
    _inherit = 'staff'
    _inherits = {'auxiliary.financing': 'auxiliary_id'}

    @api.onchange('job_id')
    def onchange_job_id(self):
        '''选择职位时带出部门和部门经理'''
        if self.job_id:
            self.department_id = self.job_id.department_id
            self.parent_id = self.job_id.department_id.manager_id

    @api.one
    @api.constrains('work_email')
    def _check_work_email(self):
        ''' 验证 work_email 合法性 '''
        if self.work_email:
            res = re.match('^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', self.work_email)
            if not res:
                raise UserError(u'请检查邮箱格式是否正确: %s' % self.work_email)

    auxiliary_id = fields.Many2one(
        string=u'辅助核算',
        comodel_name='auxiliary.financing',
        ondelete='restrict',
        required=True,
    )
    category_ids = fields.Many2many('staff.employee.category',
                                    'employee_category_rel',
                                    'emp_id',
                                    'category_id', u'标签')
    work_email = fields.Char(u'办公邮箱')
    work_phone = fields.Char(u'办公电话')
    image_medium = fields.Binary(string=u'头像', related="user_id.image", attachment=True,
                                 readonly=True, store=False)
    # 个人信息
    birthday = fields.Date(u'生日')
    identification_id = fields.Char(u'证照号码')
    is_arbeitnehmer = fields.Boolean(u'是否雇员', default='1')
    is_investoren = fields.Boolean(u'是否投资者')
    is_bsw = fields.Boolean(u'是否残疾烈属孤老')
    type_of_certification = fields.Selection([
        ('ID', u'居民身份证'),
        ('Military_ID', u'军官证'),
        ('Soldiers_Card', u'士兵证'),
        ('Police_badge', u'武警警官证'),
        ('Passport_card', u'护照'),
    ],
        u'证照类型',
        default='ID',
        required=True)
    gender = fields.Selection([
                              ('male', u'男'),
                              ('female', u'女')
                              ], u'性别')
    marital = fields.Selection([
        ('single', u'单身'),
        ('married', u'已婚'),
        ('widower', u'丧偶'),
        ('divorced', u'离异')
    ], u'婚姻状况')
    contract_ids = fields.One2many('staff.contract', 'staff_id', u'合同')
    active = fields.Boolean(u'启用', default=True)
    # 公开信息
    work_mobile = fields.Char(u'办公手机')
    department_id = fields.Many2one('staff.department', u'部门')
    parent_id = fields.Many2one('staff', u'部门经理')
    job_id = fields.Many2one('staff.job', u'职位')
    notes = fields.Text(u'其他信息')
    emergency_contact = fields.Char(u'紧急联系人')
    emergency_call = fields.Char(u'紧急联系方式')
    bank_name = fields.Char(u'开户行')
    bank_num = fields.Char(u'银行账号')

    @api.model
    def staff_contract_over_date(self):
        # 员工合同到期，发送邮件给员工 和 部门经理（如果存在）
        now = datetime.now().strftime("%Y-%m-%d")
        for Staff in self.search([]):
            if not Staff.contract_ids:
                continue

            for contract in Staff.contract_ids:
                if now == contract.over_date:
                    self.env.ref('staff.contract_over_due_date_employee').send_mail(
                        self.env.user.id)
                    if Staff.parent_id and Staff.parent_id.work_email:
                        self.env.ref('staff.contract_over_due_date_manager').send_mail(
                            self.env.user.id)

        return
