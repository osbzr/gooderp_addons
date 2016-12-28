# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  开阖软件(<http://www.osbzr.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from odoo import fields, models, api

class other_money_order(models.Model):
    _name = 'other.money.order'
    _description = u'其他收入/其他支出'

    TYPE_SELECTION = [
        ('other_pay', u'其他支出'),
        ('other_get', u'其他收入'),
    ]

    @api.model
    def create(self, values):
        # 创建单据时，更新订单类型的不同，生成不同的单据编号
        if self.env.context.get('type') == 'other_get':
            values.update({'name': self.env['ir.sequence'].next_by_code('other.get.order') or '/'})
        if self.env.context.get('type') == 'other_pay' or values.get('name', '/') == '/':
            values.update({'name': self.env['ir.sequence'].next_by_code('other.pay.order') or '/'})

        return super(other_money_order, self).create(values)

    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise UserError(u'不可以删除已经审核的单据(%s)'%order.name)

        return super(other_money_order, self).unlink()

    @api.one
    @api.depends('line_ids.amount', 'line_ids.tax_amount')
    def _compute_total_amount(self):
        # 计算应付金额/应收金额
        self.total_amount = sum((line.amount + line.tax_amount) for line in self.line_ids)

    state = fields.Selection([
                          ('draft', u'未审核'),
                          ('done', u'已审核'),
                           ], string=u'状态', readonly=True,
                             default='draft', copy=False,
                        help=u'其他收单状态标识，新建时状态为未审核;审核后状态为已审核')
    partner_id = fields.Many2one('partner', string=u'往来单位',
                                 readonly=True, ondelete='restrict',
                                 states={'draft': [('readonly', False)]},
                                 help=u'单据对应的业务伙伴，单据审核时会影响他的应收应付余额')
    date = fields.Date(string=u'单据日期', readonly=True,
                       default=lambda self: fields.Date.context_today(self),
                       states={'draft': [('readonly', False)]},
                       help=u'单据创建日期')
    name = fields.Char(string=u'单据编号', copy=False, readonly=True, default='/',
                       help=u'单据编号，创建时会根据类型自动生成')
    total_amount = fields.Float(string=u'金额', compute='_compute_total_amount',
                                store=True, readonly=True,
                                digits=dp.get_precision('Amount'),
                                help=u'本次其他收支的总金额')
    bank_id = fields.Many2one('bank.account', string=u'结算账户',
                              required=True, ondelete='restrict',
                              readonly=True, states={'draft': [('readonly', False)]},
                              help=u'本次其他收支的结算账户')
    line_ids = fields.One2many('other.money.order.line', 'other_money_id',
                               string=u'收支单行', readonly=True,
                               states={'draft': [('readonly', False)]},
                            help = u'其他收支单明细行')
    type = fields.Selection(TYPE_SELECTION, string=u'类型', readonly=True,
                            default=lambda self: self._context.get('type'),
                            states={'draft': [('readonly', False)]},
                            help=u'类型：其他收入 或者 其他支出')
    note = fields.Text(u'备注',
                       help=u'可以为该单据添加一些需要的标识信息')

    is_init = fields.Boolean(u'初始化应收应付', help=u'此单是否为初始化单')

    @api.onchange('date')
    def onchange_date(self):
        if self._context.get('type') == 'other_get':
            return {'domain': {'partner_id': [('c_category_id', '!=', False)]}}
        else:
            return {'domain': {'partner_id': [('s_category_id', '!=', False)]}}

    @api.multi
    def other_money_done(self):
        '''其他收支单的审核按钮'''
        self.ensure_one()
        if self.total_amount <= 0:
            raise UserError(u'金额应该大于0!\n金额:%s'%self.total_amount)

        # 根据单据类型更新账户余额
        if self.type == 'other_pay':
            if self.bank_id.balance < self.total_amount:
                raise UserError(u'账户余额不足!\n账户余额:%s 本次支出金额:%s' % (self.bank_id.balance, self.total_amount))
            self.bank_id.balance -= self.total_amount
        else:
            self.bank_id.balance += self.total_amount
        self.state = 'done'
        return True

    @api.multi
    def other_money_draft(self):
        '''其他收支单的反审核按钮'''
        self.ensure_one()
        # 根据单据类型更新账户余额
        if self.type == 'other_pay':
            self.bank_id.balance += self.total_amount
        else:
            if self.bank_id.balance < self.total_amount:
                raise UserError(u'账户余额不足!\n账户余额:%s 本次支出金额:%s' % (self.bank_id.balance, self.total_amount))
            self.bank_id.balance -= self.total_amount
        self.state = 'draft'
        return True


class other_money_order_line(models.Model):
    _name = 'other.money.order.line'
    _description = u'其他收支单明细'

    @api.onchange('service')
    def onchange_service(self):
        # 当选择了服务后，则自动填充上类别和金额
        if self.env.context.get('type') == 'other_get':
            self.category_id = self.service.get_categ_id.id
        elif self.env.context.get('type') == 'other_pay':
            self.category_id = self.service.pay_categ_id.id
        self.amount = self.service.price

    @api.onchange('amount', 'tax_rate')
    def onchange_tax_amount(self):
        '''当订单行的金额、税率改变时，改变税额'''
        self.tax_amount = self.amount * self.tax_rate * 0.01

    other_money_id = fields.Many2one('other.money.order',
                                u'其他收支', ondelete='cascade',
                                help=u'其他收支单行对应的其他收支单')
    service = fields.Many2one('service', u'收支项', ondelete='restrict',
                              help=u'其他收支单行上对应的服务')
    category_id = fields.Many2one('core.category',
                        u'类别', ondelete='restrict',
                        domain="[('type', '=', context.get('type'))]",
                        help=u'类型：运费、咨询费等')
    auxiliary_id = fields.Many2one('auxiliary.financing',u'辅助核算',
                                   help=u'其他收支单行上的辅助核算')
    amount = fields.Float(u'金额',
                        digits=dp.get_precision('Amount'),
                        help=u'其他收支单行上的金额')
    tax_rate = fields.Float(u'税率(%)',
                            default=lambda self:self.env.user.company_id.import_tax_rate,
                            help=u'其他收支单行上的税率')
    tax_amount = fields.Float(u'税额',
                              digits=dp.get_precision('Amount'),
                              help=u'其他收支单行上的税额')
    note = fields.Char(u'备注',
                       help=u'可以为该单据添加一些需要的标识信息')
