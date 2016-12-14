# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import float_is_zero
from odoo.exceptions import UserError

# 状态可选值
TASK_STATES = [
    ('todo', u'新建'),
    ('doing', u'正在进行'),
    ('done', u'已完成'),
    ('cancel', u'已取消'),
]

AVAILABLE_PRIORITIES = [
    ('0', u'一般'),
    ('1', u'低'),
    ('2', u'中'),
    ('3', u'高'),
]

class project(models.Model):
    _name = 'project'
    _inherits = {'auxiliary.financing': 'auxiliary_id'}

    auxiliary_id = fields.Many2one(
        string=u'辅助核算',
        comodel_name='auxiliary.financing',
        ondelete='cascade',
        required=True,
    )

    task_ids = fields.One2many(
        string=u'任务',
        comodel_name='task',
        inverse_name='project_id',
    )

    customer_id = fields.Many2one(
        string=u'客户',
        comodel_name='partner',
        ondelete='restrict',
    )

    invoice_ids = fields.One2many(
        string=u'发票行',
        comodel_name='project.invoice',
        inverse_name='project_id',
    )


class project_invoice(models.Model):
    _name = 'project.invoice'

    @api.one
    @api.depends('tax_rate', 'amount')
    def _compute_tax_amount(self):
        '''计算税额'''
        if self.tax_rate > 100:
            raise UserError('税率不能输入超过100的数\n当前税率:%s'%self.tax_rate)
        if self.tax_rate < 0:
            raise UserError('税率不能输入负数\n当前税率:%s'%self.tax_rate)
        self.tax_amount = self.amount / (100 + self.tax_rate) * self.tax_rate

    project_id = fields.Many2one(
        string=u'项目',
        comodel_name='project',
        ondelete='cascade',
   )

    tax_rate = fields.Float(
        string=u'税率',
        default=lambda self: self.env.user.company_id.output_tax_rate,
        help=u'默认值取公司销项税率',
    )

    tax_amount = fields.Float(
        string=u'税额',
        compute=_compute_tax_amount,
    )

    amount = fields.Float(
        string=u'金额',
        help=u'含税金额',
    )

    date_due = fields.Date(
        string='到期日',
        default=lambda self: fields.Date.context_today(self),
        required=True,
        help=u'收款截止日期',
    )

    invoice_id = fields.Many2one(
        string=u'发票号',
        comodel_name='money.invoice',
        readonly=True,
        copy=False,
        ondelete='set null',
        help=u'产生的发票号',
    )

    def _get_invoice_vals(self, category_id, project_id, amount, tax_amount):
        '''返回创建 money_invoice 时所需数据'''
        return {
            'name': project_id.name,
            'partner_id': project_id.customer_id and project_id.customer_id.id,
            'category_id': category_id.id,
            'auxiliary_id': project_id.auxiliary_id.id,
            'date': fields.Date.context_today(self),
            'amount': amount,
            'reconciled': 0,
            'to_reconcile': amount,
            'tax_amount': tax_amount,
            'date_due': self.date_due,
            'state': 'draft',
        }

    @api.multi
    def make_invoice(self):
        '''生成结算单'''
        for line in self:
            invoice_id = False
            if not line.project_id.customer_id:
                return
            category = self.env.ref('money.core_category_sale')
            if not float_is_zero(self.amount, 2):
                invoice_id = self.env['money.invoice'].create(
                    self._get_invoice_vals(category, line.project_id, line.amount, line.tax_amount)
                )
                line.invoice_id = invoice_id.id
            return invoice_id


class task(models.Model):
    _name = 'task'
    _inherit = ['mail.thread']
    _order = 'sequence, priority desc, id'

    @api.multi
    def _compute_hours(self):
        '''计算任务的实际时间'''
        for task in self:
            for line in self.env['timeline'].search(
                                [('task_id', '=', task.id)]):
                task.hours += line.hours

    name = fields.Char(
        string=u'名称',
        required=True,
    )

    user_id = fields.Many2one(
        string=u'指派给',
        comodel_name='res.users',
    )

    project_id = fields.Many2one(
        string=u'项目',
        comodel_name='project',
        ondelete='cascade',
    )

    timeline_ids = fields.One2many(
        string=u'工作记录',
        comodel_name='timeline',
        inverse_name='task_id',
    )

    next_action = fields.Char(
        string=u'下一步计划',
        required=False,
        help=u'针对此任务下一步的计划',
        track_visibility='onchange',
    )

    next_datetime = fields.Datetime(
        string=u'下一步计划时间',
        help=u'下一步计划预计开始的时间',
        track_visibility='onchange',
    )

    status = fields.Many2one('task.status',
                             string=u'状态',
                             track_visibility='onchange')
    plan_hours = fields.Float(u'计划时间')
    hours = fields.Float(u'实际时间',
                         compute=_compute_hours)
    sequence = fields.Integer(u'顺序')
    is_schedule = fields.Boolean(u'列入计划')
    note = fields.Text(u'描述')
    priority = fields.Selection(AVAILABLE_PRIORITIES,
                                string=u'优先级',
                                default=AVAILABLE_PRIORITIES[0][0])
    color = fields.Integer('Color Index',
                           default=0)

    @api.multi
    def assign_to_me(self):
        '''将任务指派给自己，并修改状态'''
        self.ensure_one()
        next_status = self.env['task.status'].search([('state', '=', 'doing')])
        self.user_id = self.env.user
        if next_status:
            self.status = next_status[0]

class task_status(models.Model):
    _name = 'task.status'
    _order = 'sequence, id'
    
    name = fields.Char(u'名称')
    state = fields.Selection(TASK_STATES,
                             string=u'任务状态',
                             default='doing')
    sequence = fields.Integer(u'顺序')


class timesheet(models.Model):
    _name = 'timesheet'

    date = fields.Date(
        string=u'日期',
        required=True,
        readonly=True,
        default=fields.Date.context_today)

    user_id = fields.Many2one(
        string=u'用户',
        required=True,
        readonly=True,
        default=lambda self: self.env.user,
        comodel_name='res.users',
    )

    timeline_ids = fields.One2many(
        string=u'工作记录',
        comodel_name='timeline',
        inverse_name='timesheet_id',
    )

    task_ids = fields.Many2many(
        string=u'待办事项',
        required=False,
        readonly=False,
        default=lambda self: [(4, t.id) for t in self.env['task'].search(
                    [('user_id','=',self.env.user.id),
                     ('status.state','=','doing')])],
        help=False,
        comodel_name='task',
        domain=[],
        context={},
        limit=None
    )
    _sql_constraints = [
        ('user_uniq', 'unique(user_id,date)', '同一个人一天只能创建一个工作日志')
    ]

    @api.multi
    def name_get(self):
        ret = []
        for s in self:
            ret.append((s.id, '%s %s' % (s.user_id.name, s.date)))
        return ret


class timeline(models.Model):
    _name = 'timeline'

    timesheet_id = fields.Many2one(
        string=u'记录表',
        comodel_name='timesheet',
        ondelete='cascade',
    )

    task_id = fields.Many2one(
        string=u'任务',
        required=True,
        readonly=False,
        comodel_name='task',
    )

    project_id = fields.Many2one(
        string=u'项目',
        related='task_id.project_id',
        ondelete='cascade',
    )

    user_id = fields.Many2one(
        string=u'指派给',
        comodel_name='res.users',
    )

    hours = fields.Float(
        string=u'小时数',
        default=0.5,
        digits=(16, 1),
        help=u'实际花的小时数',
    )

    just_done = fields.Char(
        string=u'具体工作内容',
        required=True,
        help=u'在此时长内针对此任务实际完成的工作内容',
    )
# TODO 以下三个字段用于更新task的同名字段
    next_action = fields.Char(
        string=u'下一步计划',
        required=False,
        help=u'针对此任务下一步的计划',
    )

    next_datetime = fields.Datetime(
        string=u'下一步计划时间',
        help=u'下一步计划预计开始的时间',
    )
    set_status = fields.Many2one('task.status',
                             string=u'状态更新到')

    @api.model
    def create(self, vals):
        '''创建工作记录时，更新对应task的status等字段'''
        res = super(timeline, self).create(vals)
        set_status = vals.get('set_status')
        task_id = vals.get('task_id')
        next_action = vals.get('next_action')
        next_datetime = vals.get('next_datetime')
        task = self.env['task'].search([('id', '=', task_id)])
        if set_status:
            task.write({'status': set_status})
        if next_action:
            task.write({'next_action': next_action})
        if next_datetime:
            task.write({'next_datetime': next_datetime})
        return res
