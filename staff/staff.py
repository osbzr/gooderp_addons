# -*- coding: utf-8 -*-
from openerp import fields, models, api

class staff_department(models.Model):
    _name = "staff.department"
    
    name = fields.Char(u'部门名称',required=True)
    manager_id = fields.Many2one('staff',u'部门经理')
    member_ids = fields.One2many('staff', 'department_id', u'部门成员')
    parent_id = fields.Many2one('staff.department',u'上级部门')
    child_ids = fields.One2many('staff.department', 'parent_id', u'下级部门')
    jobs_ids = fields.One2many('staff.job','department_id',u'职位')
    note = fields.Text(u'备注')


class staff_job(models.Model):
    _name = "staff.job"
    
    name = fields.Char(u'职位',required=True)
    note = fields.Text(u'描述')
    department_id = fields.Many2one('staff.department',u'部门')


class staff_employee_category(models.Model):
    _name = "staff.employee.category"

    name = fields.Char(u'名称')
    parent_id = fields.Many2one('staff.employee.category', u'上级标签', select=True)
    chield_ids = fields.One2many('staff.employee.category','parent_id',u'下级标签')
    employee_ids = fields.Many2many('staff',
                                    'employee_category_rel',
                                    'category_id',
                                    'emp_id',u'员工')


class staff(models.Model):
    _inherit = 'staff'

    @api.one
    @api.depends('image_medium')
    def _get_image(self):
        self.image_medium = self.user_id.image
    
    @api.one
    @api.onchange('job_id')
    def onchange_job_id(self):
        '''选择职位时带出部门和部门经理'''
        if self.job_id:
            self.department_id = self.job_id.department_id
            self.parent_id = self.job_id.department_id.manager_id

    name = fields.Char(u'名称',required=True)
    category_ids = fields.Many2many('staff.employee.category', 
                                    'employee_category_rel', 
                                    'emp_id', 
                                    'category_id', u'标签')
    work_email = fields.Char(u'办公邮箱')
    work_phone = fields.Char(u'办公电话')
    user_id = fields.Many2one('res.users',u'对应用户')
    image_medium = fields.Binary(string='头像',compute=_get_image)
    #个人信息
    country_id = fields.Many2one('country',u'国籍')
    birthday = fields.Date(u'生日')
    identification_id = fields.Char(u'身份证号')
    passport_id = fields.Char(u'护照号')
    gender =fields.Selection([
                              ('male',u'男'),
                              ('female',u'女')
                              ],u'性别')
    marital = fields.Selection([
                                ('single',u'单身'),
                                ('married',u'已婚'),
                                ('widower',u'丧偶'),
                                ('divorced',u'离异')
                                ],u'婚姻状况')
    contract_ids=fields.One2many('staff.contract', 'staff_id', u'合同')
    active = fields.Boolean(u'生效',default='1')
    #公开信息
    work_mobile = fields.Char(u'办公手机')
    department_id = fields.Many2one('staff.department',u'部门')
    parent_id = fields.Many2one('staff',u'部门经理')
    job_id = fields.Many2one('staff.job',u'职位')
    notes = fields.Text(u'其他信息')


class res_users(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'
    
    employee_ids =  fields.One2many('staff', 'user_id', u'对应员工')

    
    
