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

from openerp.exceptions import except_orm
from openerp import fields, models, api

class other_money_order(models.Model):
    _name = 'other.money.order'
    _description = u'其他收入/其他支出'

    TYPE_SELECTION = [
        ('other_pay', u'其他收入'),
        ('other_get', u'其他支出'),
    ]

    @api.model
    def create(self, values):
        # 创建单据时，更新订单类型的不同，生成不同的单据编号
        if self._context.get('type') == 'other_get':
            values.update({'name': self.env['ir.sequence'].get('other.get.order') or '/'})
        if self._context.get('type') == 'other_pay' or values.get('name', '/') == '/':
            values.update({'name': self.env['ir.sequence'].get('other.pay.order') or '/'})

        return super(other_money_order, self).create(values)

    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise except_orm(u'错误', u'不可以删除已经审核的单据')

        return super(other_money_order, self).unlink()

    @api.one
    @api.depends('line_ids.amount')
    def _compute_total_amount(self):
        # 计算应付金额/应收金额
        self.total_amount = sum(line.amount for line in self.line_ids)

    state = fields.Selection([
                          ('draft', u'未审核'),
                          ('done', u'已审核'),
                           ], string=u'状态', readonly=True,
                             default='draft', copy=False)
    partner_id = fields.Many2one('partner', string=u'往来单位', readonly=True,
                                 states={'draft': [('readonly', False)]})
    date = fields.Date(string=u'单据日期', readonly=True,
                       default=lambda self: fields.Date.context_today(self),
                       states={'draft': [('readonly', False)]})
    name = fields.Char(string=u'单据编号', copy=False, readonly=True, default='/')
    total_amount = fields.Float(string=u'金额', compute='_compute_total_amount',
                                store=True, readonly=True)
    bank_id = fields.Many2one('bank.account', string=u'结算账户', required=True,
                              readonly=True, states={'draft': [('readonly', False)]})
    line_ids = fields.One2many('other.money.order.line', 'other_money_id',
                               string=u'收支单行', readonly=True,
                               states={'draft': [('readonly', False)]})
    type = fields.Selection(TYPE_SELECTION, string=u'类型', readonly=True,
                            default=lambda self: self._context.get('type'),
                            states={'draft': [('readonly', False)]})

    @api.onchange('date')
    def onchange_date(self):
        if self._context.get('type') == 'other_get':
            return {'domain': {'partner_id': [('c_category_id', '!=', False)]}}
        else:
            return {'domain': {'partner_id': [('s_category_id', '!=', False)]}}

    @api.onchange('partner_id')
    def onchange_partner(self):
        '''
        根据所选业务伙伴源单填充行
        '''
        self.line_ids = []
        lines = []
        for invoice in self.env['money.invoice'].search([('partner_id', '=', self.partner_id.id), ('to_reconcile', '!=', 0)]):
            lines.append((0, 0, {
                'category_id': invoice.category_id.id,
                'source_id': invoice.id,
                'amount': invoice.to_reconcile,
                                   }))
        self.line_ids = lines

    @api.multi
    def other_money_done(self):
        '''其他收支单的审核按钮'''
        for other in self:
            if other.total_amount <= 0:
                raise except_orm(u'错误', u'金额应该大于0')
            for line in other.line_ids:
                # 针对源单付款，则更新源单和供应商应付
                if line.source_id:
                    if line.amount > line.source_id.to_reconcile:
                        raise except_orm(u'错误', u'核销金额大于源单未核销金额')
                    else:
                        line.source_id.to_reconcile -= line.amount
                        other.partner_id.payable -= line.amount
            # 根据单据类型更新账户余额
            if other.type == 'other_pay':
                if other.bank_id.balance < other.total_amount:
                    raise except_orm(u'错误', u'账户余额不足')
                other.bank_id.balance -= other.total_amount
            else:
                other.bank_id.balance += other.total_amount
            other.state = 'done'
        return True

    @api.multi
    def other_money_draft(self):
        '''其他收支单的反审核按钮'''
        for other in self:
            for line in other.line_ids:
                # 针对源单付款，则更新源单和供应商应付
                if line.source_id:
                    line.source_id.to_reconcile += line.amount
                    other.partner_id.payable += line.amount
            # 根据单据类型更新账户余额
            if other.type == 'other_pay':
                other.bank_id.balance += other.total_amount
            else:
                if other.bank_id.balance < other.total_amount:
                    raise except_orm(u'错误', u'账户余额不足')
                other.bank_id.balance -= other.total_amount
            other.state = 'draft'
        return True

#     @api.multi
#     def print_other_money_order(self):
#         '''打印 其他收入/支出单'''
#         assert len(self._ids) == 1, '一次执行只能有一个id'
#         return self.env['report'].get_action('money.report_other_money_order')

class other_money_order_line(models.Model):
    _name = 'other.money.order.line'
    _description = u'其他收支单明细'

    other_money_id = fields.Many2one('other.money.order', string=u'其他收支')
    category_id = fields.Many2one('core.category', u'类别', domain="[('type', '=', context.get('type'))]")
    source_id = fields.Many2one('money.invoice', string=u'源单')
    amount = fields.Float(string=u'金额')
    note = fields.Char(string=u'备注')
