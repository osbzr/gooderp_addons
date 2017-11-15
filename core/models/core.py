# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
from odoo.exceptions import UserError

# 单据自动编号，避免在所有单据对象上重载

create_original = models.BaseModel.create


@api.model
@api.returns('self', lambda value: value.id)
def create(self, vals):
    if not self._name.split('.')[0] in ['mail', 'ir', 'res'] and not vals.get('name'):
        next_name = self.env['ir.sequence'].next_by_code(self._name)
        if next_name:
            vals.update({'name': next_name})
    record_id = create_original(self, vals)
    return record_id


models.BaseModel.create = create


# 不能删除已审核的单据，避免在所有单据对象上重载

unlink_original = models.BaseModel.unlink


@api.multi
def unlink(self):
    for record in self:
        if 'state' in record._fields.keys():
            if record.state == 'done':
                raise UserError(u'不能删除已审核的单据！')

        unlink_original(record)


models.BaseModel.unlink = unlink


class BaseModelExtend(models.AbstractModel):
    _name = 'basemodel.extend'

    '''
    增加作废方法
    '''
    def _register_hook(self):
        '''
        Register method in BaseModel 
        '''
        @api.multi
        def action_cancel(self):
            for record in self:
                if self.state != 'draft':
                    raise UserError(u'只能作废草稿状态的单据')
                else:
                    self.state = 'cancel'
            return True
        models.BaseModel.action_cancel = action_cancel
        return super(BaseModelExtend, self)._register_hook()


# 分类的类别

CORE_CATEGORY_TYPE = [('customer', u'客户'),
                      ('supplier', u'供应商'),
                      ('goods', u'商品'),
                      ('expense', u'采购'),
                      ('income', u'收入'),
                      ('other_pay', u'其他支出'),
                      ('other_get', u'其他收入'),
                      ('attribute', u'属性'),
                      ('finance', u'核算')]

# 当客户要求下拉字段可编辑，可使用此表存储可选值，按type分类，在字段上用domain和context筛选


class CoreValue(models.Model):
    _name = 'core.value'
    _description = u'可选值'

    name = fields.Char(u'名称', required=True)
    type = fields.Char(u'类型', required=True,
                       default=lambda self: self._context.get('type'))
    note = fields.Text(u'备注', help=u'此字段用于详细描述该可选值的意义，或者使用一些特殊字符作为程序控制的标识')
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    _sql_constraints = [
        ('name_uniq', 'unique(type,name)', '同类可选值不能重名')
    ]


class CoreCategory(models.Model):
    _name = 'core.category'
    _description = u'类别'
    _order = 'type, name'

    name = fields.Char(u'名称', required=True)
    type = fields.Selection(CORE_CATEGORY_TYPE, u'类型',
                            required=True,
                            default=lambda self: self._context.get('type'))
    note = fields.Text(u'备注')
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    _sql_constraints = [
        ('name_uniq', 'unique(type, name)', '同类型的类别不能重名')
    ]


class Uom(models.Model):
    _name = 'uom'
    _description = u'计量单位'

    name = fields.Char(u'名称', required=True)
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '单位不能重名')
    ]


class SettleMode(models.Model):
    _name = 'settle.mode'
    _description = u'结算方式'

    name = fields.Char(u'名称', required=True)
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '结算方式不能重名')
    ]


class Staff(models.Model):
    _name = 'staff'
    _description = u'员工'

    user_id = fields.Many2one('res.users', u'对应用户')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.one
    @api.constrains('user_id')
    def _check_user_id(self):
        '''一个员工只能对应一个用户'''
        if self.user_id:
            staffs = self.env['staff'].search(
                [('user_id', '=', self.user_id.id)])
            if len(staffs) > 1:
                raise UserError(u'用户 %s 已有对应员工' % self.user_id.name)


class BankAccount(models.Model):
    _name = 'bank.account'
    _description = u'账户'

    name = fields.Char(u'名称', required=True)
    balance = fields.Float(u'余额', readonly=True,
                           digits=dp.get_precision('Amount'))
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '账户不能重名')
    ]


class Service(models.Model):
    ''' 是对其他收支业务的更细分类 '''
    _name = 'service'
    _description = u'收支项'

    name = fields.Char(u'名称', required=True)
    get_categ_id = fields.Many2one('core.category',
                                   u'收入类别', ondelete='restrict',
                                   domain="[('type', '=', 'other_get')]",
                                   context={'type': 'other_get'})
    pay_categ_id = fields.Many2one('core.category',
                                   u'支出类别', ondelete='restrict',
                                   domain="[('type', '=', 'other_pay')]",
                                   context={'type': 'other_pay'})
    price = fields.Float(u'价格', required=True)
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
