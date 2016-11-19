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

# 分类的类别

CORE_CATEGORY_TYPE = [('customer', u'客户'),
                      ('supplier', u'供应商'),
                      ('goods', u'商品'),
                      ('expense', u'采购'),
                      ('income', u'收入'),
                      ('other_pay', u'其他支出'),
                      ('other_get', u'其他收入'),
                      ('attribute', u'属性')]

# 当客户要求下拉字段可编辑，可使用此表存储可选值，按type分类，在字段上用domain和context筛选


class core_value(models.Model):
    _name = 'core.value'
    name = fields.Char(u'名称', required=True)
    type = fields.Char(u'类型', required=True,
                       default=lambda self: self._context.get('type'))
    note = fields.Text(u'备注', help=u'此字段用于详细描述该可选值的意义，或者使用一些特殊字符作为程序控制的标识')
    _sql_constraints = [
        ('name_uniq', 'unique(type,name)', '同类可选值不能重名')
    ]


class core_category(models.Model):
    _name = 'core.category'
    name = fields.Char(u'名称', required=True)
    type = fields.Selection(CORE_CATEGORY_TYPE, u'类型',
                            required=True,
                            default=lambda self: self._context.get('type'))
    note = fields.Text(u'备注')
    _sql_constraints = [
        ('name_uniq', 'unique(type, name)', '同类型的类别不能重名')
    ]


class uom(models.Model):
    _name = 'uom'
    name = fields.Char(u'名称', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '单位不能重名')
    ]


class settle_mode(models.Model):
    _name = 'settle.mode'
    name = fields.Char(u'名称', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '结算方式不能重名')
    ]


class staff(models.Model):
    _name = 'staff'

    user_id = fields.Many2one('res.users', u'对应用户')

    @api.one
    @api.constrains('user_id')
    def _check_user_id(self):
        '''一个员工只能对应一个用户'''
        if self.user_id:
            staffs = self.env['staff'].search([('user_id', '=', self.user_id.id)])
            if len(staffs) > 1:
                raise UserError('用户 %s 已有对应员工' % self.user_id.name)


class bank_account(models.Model):
    _name = 'bank.account'
    name = fields.Char(u'名称', required=True)
    balance = fields.Float(u'余额', readonly=True,
                           digits=dp.get_precision('Amount'))

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '账户不能重名')
    ]



class service(models.Model):
    ''' 是对其他收支业务的更细分类 '''
    _name = 'service'
    _description = u'服务'

    name = fields.Char(u'名称', required=True)
    get_categ_id = fields.Many2one('core.category',
                                   u'收入类别', ondelete='restrict',
                                   domain="[('type', '=', 'other_get')]")
    pay_categ_id = fields.Many2one('core.category',
                                   u'支出类别', ondelete='restrict',
                                   domain="[('type', '=', 'other_pay')]")
    price = fields.Float(u'价格', required=True)

