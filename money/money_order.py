# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016  开阖软件(<http://osbzr.com>).
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


class money_order(models.Model):
    _name = 'money.order'
    _description = u"收付款单"

    TYPE_SELECTION = [
        ('pay', u'付款'),
        ('get', u'收款'),
    ]

    @api.model
    def create(self, values):
        # 创建单据时，根据订单类型的不同，生成不同的单据编号
        if self._context.get('type') == 'pay':
            values.update({'name': self.env['ir.sequence'].get('pay.order')})
        else:
            values.update({'name': self.env['ir.sequence'].get('get.order')})

        return super(money_order, self).create(values)

    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise except_orm(u'错误', u'不可以删除已经审核的单据')

        return super(money_order, self).unlink()

    @api.one
    @api.depends('discount_amount',
                 'line_ids.amount',
                 'source_ids.this_reconcile')
    def _compute_advance_payment(self):
        amount, this_reconcile = 0.0, 0.0
        for line in self.line_ids:
            amount += line.amount
        for line in self.source_ids:
            this_reconcile += line.this_reconcile
        self.advance_payment = amount - this_reconcile + self.discount_amount
        self.amount = amount

    state = fields.Selection([
                          ('draft', u'未审核'),
                          ('done', u'已审核'),
                          ], string=u'状态', readonly=True,
                             default='draft', copy=False)
    partner_id = fields.Many2one('partner', string=u'业务伙伴', required=True,
                                 readonly=True,
                                 states={'draft': [('readonly', False)]})
    date = fields.Date(string=u'单据日期', readonly=True,
                       default=lambda self: fields.Date.context_today(self),
                       states={'draft': [('readonly', False)]})
    name = fields.Char(string=u'单据编号', copy=False, readonly=True)
    note = fields.Text(string=u'备注')
    discount_amount = fields.Float(string=u'整单折扣', readonly=True,
                                   states={'draft': [('readonly', False)]})
    line_ids = fields.One2many('money.order.line', 'money_id',
                               string=u'收付款单行', readonly=True,
                               states={'draft': [('readonly', False)]})
    source_ids = fields.One2many('source.order.line', 'money_id',
                                 string=u'源单行', readonly=True,
                                 states={'draft': [('readonly', False)]})
    type = fields.Selection(TYPE_SELECTION, string=u'类型',
                            default=lambda self: self._context.get('type'))
    amount = fields.Float(string=u'总金额', compute='_compute_advance_payment',
                          store=True, readonly=True)
    advance_payment = fields.Float(string=u'本次预收款',
                                   compute='_compute_advance_payment',
                                   store=True, readonly=True)
    to_reconcile = fields.Float(string=u'未核销预收款')
    reconciled = fields.Float(string=u'已核销预收款')

    @api.onchange('date')
    def onchange_date(self):
        if self._context.get('type') == 'get':
            return {'domain': {'partner_id': [('c_category_id', '!=', False)]}}
        else:
            return {'domain': {'partner_id': [('s_category_id', '!=', False)]}}

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            return {}

        source_lines = []
        self.source_ids = []
        money_invoice = self.env['money.invoice']
        if self.env.context.get('type') == 'get':
            money_invoice = self.env['money.invoice'].search([
                                    ('partner_id', '=', self.partner_id.id),
                                    ('category_id.type', '=', 'income'),
                                    ('to_reconcile', '!=', 0)])
        if self.env.context.get('type') == 'pay':
            money_invoice = self.env['money.invoice'].search([
                                    ('partner_id', '=', self.partner_id.id),
                                    ('category_id.type', '=', 'expense'),
                                    ('to_reconcile', '!=', 0)])
        for invoice in money_invoice:
            source_lines.append({
                   'name': invoice.id,
                   'category_id': invoice.category_id.id,
                   'amount': invoice.amount,
                   'date': invoice.date,
                   'reconciled': invoice.reconciled,
                   'to_reconcile': invoice.to_reconcile,
                   'this_reconcile': invoice.to_reconcile,
                   'date_due': invoice.date_due,
                   })
        self.source_ids = source_lines

    @api.multi
    def money_order_done(self):
        '''对收支单的审核按钮'''
        for order in self:
            if order.advance_payment < 0:
                raise except_orm(u'错误', u'核销金额不能大于付款金额')

            order.to_reconcile = order.advance_payment
            order.reconciled = order.amount - order.advance_payment

            total = 0
            for line in order.line_ids:
                if order.type == 'pay':  # 付款账号余额减少, 退款账号余额增加
                    if line.bank_id.balance < line.amount:
                        raise except_orm(u'错误', u'账户余额不足')
                    line.bank_id.balance -= line.amount
                else:  # 收款账号余额增加, 退款账号余额减少
                    line.bank_id.balance += line.amount
                total += line.amount

            if order.type == 'pay':
                order.partner_id.payable -= total
            else:
                order.partner_id.receivable -= total

            # 更新源单的未核销金额、已核销金额
            for source in order.source_ids:
                if abs(source.to_reconcile) < source.this_reconcile:
                    raise except_orm(u'错误', u'本次核销金额不能大于未核销金额')

                source.to_reconcile = (source.to_reconcile - 
                                       source.this_reconcile)
                source.name.to_reconcile = source.to_reconcile
                source.name.reconciled = (source.reconciled + 
                                          source.this_reconcile)

            order.state = 'done'
        return True

    @api.multi
    def money_order_draft(self):
        for order in self:
            order.to_reconcile = 0
            order.reconciled = 0

            total = 0
            for line in order.line_ids:
                if order.type == 'pay':  # 付款账号余额减少
                    line.bank_id.balance += line.amount
                else:  # 收款账号余额增加
                    if line.bank_id.balance < line.amount:
                        raise except_orm(u'错误', u'账户余额不足')
                    line.bank_id.balance -= line.amount
                total += line.amount

            if order.type == 'pay':
                order.partner_id.payable += total
            else:
                order.partner_id.receivable += total

            for source in order.source_ids:
                source.name.to_reconcile = (source.to_reconcile + 
                                            source.this_reconcile)
                source.name.reconciled = (source.reconciled - 
                                          source.this_reconcile)

            order.state = 'draft'
        return True

#     @api.multi
#     def print_money_order(self):
#         return True


class money_order_line(models.Model):
    _name = 'money.order.line'
    _description = u'收付款单明细'

    money_id = fields.Many2one('money.order', string=u'收付款单')
    bank_id = fields.Many2one('bank.account', string=u'结算账户', required=True)
    amount = fields.Float(string=u'金额')
    mode_id = fields.Many2one('settle.mode', string=u'结算方式')
    number = fields.Char(string=u'结算号')
    note = fields.Char(string=u'备注')


class money_invoice(models.Model):
    _name = 'money.invoice'
    _description = u'源单'

    state = fields.Selection([
                          ('draft', u'草稿'),
                          ('done', u'完成')
                          ], string=u'状态', readonly=True,
                          default='draft', copy=False)
    partner_id = fields.Many2one('partner', string=u'业务伙伴',
                                 required=True, readonly=True)
    name = fields.Char(string=u'订单编号', copy=False,
                       readonly=True, required=True)
    category_id = fields.Many2one('core.category', string=u'类别', readonly=True)
    date = fields.Date(string=u'单据日期', readonly=True,
                       default=lambda self: fields.Date.context_today(self))
    amount = fields.Float(string=u'单据金额', readonly=True)
    reconciled = fields.Float(string=u'已核销金额', readonly=True)
    to_reconcile = fields.Float(string=u'未核销金额', readonly=True)
    date_due = fields.Date(string=u'到期日')

    @api.multi
    def money_invoice_done(self):
        for inv in self:
            inv.state = 'done'
            if self.category_id.type == 'income':
                inv.partner_id.receivable += inv.amount
            if self.category_id.type == 'expense':
                inv.partner_id.payable += inv.amount

    @api.multi
    def money_invoice_draft(self):
        for inv in self:
            inv.state = 'draft'
            if self.category_id.type == 'income':
                inv.partner_id.receivable -= inv.amount
            if self.category_id.type == 'expense':
                inv.partner_id.payable -= inv.amount

    @api.model
    def create(self, values):
        new_id = super(money_invoice, self).create(values)
        if not self.env.user.company_id.draft_invoice:
            new_id.money_invoice_done()
        return new_id

    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.state == 'done':
                raise except_orm(u'错误', u'不可以删除已经审核的单据')

        return super(money_invoice, self).unlink()


class source_order_line(models.Model):
    _name = 'source.order.line'
    _description = u'源单明细'

    money_id = fields.Many2one('money.order', string=u'收付款单')  # 收付款单上的源单明细
    receivable_reconcile_id = fields.Many2one('reconcile.order',
                                              string=u'核销单')  # 核销单上的应收源单明细
    payable_reconcile_id = fields.Many2one('reconcile.order',
                                           string=u'核销单')  # 核销单上的应付源单明细
    name = fields.Many2one('money.invoice', string=u'源单编号',
                           copy=False, required=True)
    category_id = fields.Many2one('core.category', string=u'类别', required=True)
    date = fields.Date(string=u'单据日期')
    amount = fields.Float(string=u'单据金额')
    reconciled = fields.Float(string=u'已核销金额')
    to_reconcile = fields.Float(string=u'未核销金额')
    this_reconcile = fields.Float(string=u'本次核销金额')
    date_due = fields.Date(string=u'到期日')


class reconcile_order(models.Model):
    _name = 'reconcile.order'
    _description = u'核销单'

    TYPE_SELECTION = [
        ('adv_pay_to_get', u'预收冲应收'),
        ('adv_get_to_pay', u'预付冲应付'),
        ('get_to_pay', u'应收冲应付'),
        ('get_to_get', u'应收转应收'),
        ('pay_to_pay', u'应付转应付'),
    ]

    @api.model
    def create(self, values):
        # 生成订单编号
        if values.get('name', '/') == '/':
            values.update({'name': self.env['ir.sequence'].get(self._name)})

        return super(reconcile_order, self).create(values)

    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise except_orm(u'错误', u'不可以删除已经审核的单据')

        return super(reconcile_order, self).unlink()

    state = fields.Selection([
                          ('draft', u'未审核'),
                          ('done', u'已审核'),
                          ], string=u'状态', readonly=True,
                          default='draft', copy=False)
    partner_id = fields.Many2one('partner', string=u'业务伙伴', required=True,
                                 readonly=True,
                                 states={'draft': [('readonly', False)]})
    to_partner_id = fields.Many2one('partner', string=u'转入往来单位', readonly=True,
                                    states={'draft': [('readonly', False)]})
    advance_payment_ids = fields.One2many(
                            'advance.payment', 'pay_reconcile_id',
                            string=u'预收单行', readonly=True,
                            states={'draft': [('readonly', False)]})
    receivable_source_ids = fields.One2many(
                            'source.order.line', 'receivable_reconcile_id',
                             string=u'应收源单行', readonly=True,
                             states={'draft': [('readonly', False)]})
    payable_source_ids = fields.One2many(
                            'source.order.line', 'payable_reconcile_id',
                            string=u'应付源单行', readonly=True,
                            states={'draft': [('readonly', False)]})
    business_type = fields.Selection(TYPE_SELECTION, string=u'业务类型',
                                     readonly=True,
                                     states={'draft': [('readonly', False)]})
    name = fields.Char(string=u'单据编号', copy=False, readonly=True, default='/')
    date = fields.Date(string=u'单据日期', readonly=True,
                       default=lambda self: fields.Date.context_today(self),
                       states={'draft': [('readonly', False)]})
    note = fields.Text(string=u'备注')

    @api.multi
    def _get_money_order(self, way='get'):
        money_orders = self.env['money.order'].search(
                                    [('partner_id', '=', self.partner_id.id),
                                    ('type', '=', way),
                                    ('state', '=', 'done'),
                                    ('to_reconcile', '!=', 0)])
        result = []
        for order in money_orders:
            result.append((0, 0, {
                   'name': order.id,
                   'amount': order.amount,
                   'date': order.date,
                   'reconciled': order.reconciled,
                   'to_reconcile': order.to_reconcile,
                   'this_reconcile': order.to_reconcile,
                   }))
        return result

    @api.multi
    def _get_money_invoice(self, way='income'):
        money_invoice = self.env['money.invoice'].search([
                                    ('category_id.type', '=', way),
                                    ('partner_id', '=', self.partner_id.id),
                                    ('to_reconcile', '!=', 0)])
        result = []
        for invoice in money_invoice:
            result.append((0, 0, {
                   'name': invoice.id,
                   'category_id': invoice.category_id.id,
                   'amount': invoice.amount,
                   'date': invoice.date,
                   'reconciled': invoice.reconciled,
                   'to_reconcile': invoice.to_reconcile,
                   'date_due': invoice.date_due,
                   'this_reconcile': invoice.to_reconcile,
                   }))
        return result

    @api.onchange('partner_id', 'to_partner_id', 'business_type')
    def onchange_partner_id(self):
        if not self.partner_id or not self.business_type:
            return {}

        # 先清空之前填充的数据
        self.advance_payment_ids = None
        self.receivable_source_ids = None
        self.payable_source_ids = None

        money_order = self.env['money.order']
        money_invoice = self.env['money.invoice']

        if self.business_type == 'adv_pay_to_get':  # 预收冲应收
            self.advance_payment_ids = self._get_money_order('get')
            self.receivable_source_ids = self._get_money_invoice('income')

        if self.business_type == 'adv_get_to_pay':  # 预付冲应付
            self.advance_payment_ids = self._get_money_order('pay')
            self.payable_source_ids = self._get_money_invoice('expense')

        if self.business_type == 'get_to_pay':  # 应收冲应付
            self.receivable_source_ids = self._get_money_invoice('income')
            self.payable_source_ids = self._get_money_invoice('expense')

        if self.business_type == 'get_to_get':  # 应收转应收
            self.receivable_source_ids = self._get_money_invoice('income')

        if self.business_type == 'pay_to_pay':  # 应付转应付
            self.payable_source_ids = self._get_money_invoice('expense')

    @api.multi
    def _get_or_pay(self, line, business_type,
                    partner_id, to_partner_id, name):
        if line.this_reconcile > line.to_reconcile:
            raise except_orm(u'错误', u'核销金额不能大于未核销金额')
        # 更新每一行的已核销余额、未核销余额
        line.name.to_reconcile -= line.this_reconcile
        line.name.reconciled += line.this_reconcile

        # 应收转应收、应付转应付
        if business_type in ['get_to_get', 'pay_to_pay']:
            self.env['money.invoice'].create({
                   'name': name,
                   'category_id': line.category_id.id,
                   'amount': line.this_reconcile,
                   'date': line.date,
                   'reconciled': 0,  # 已核销金额
                   'to_reconcile': line.this_reconcile,  # 未核销金额
                   'date_due': line.date_due,
                   'partner_id': to_partner_id.id,
                   })

            if business_type == 'get_to_get':
                to_partner_id.receivable += line.this_reconcile
                partner_id.receivable -= line.this_reconcile
            if business_type == 'pay_to_pay':
                to_partner_id.payable += line.this_reconcile
                partner_id.payable -= line.this_reconcile

        return True

    @api.multi
    def reconcile_order_done(self):
        '''核销单的审核按钮'''
        # 核销金额不能大于未核销金额
        for order in self:
            if order.state == 'done':
                continue
            order_reconcile, invoice_reconcile = 0, 0
            if (self.business_type in ['get_to_get', 'pay_to_pay'] and
                order.partner_id.id == order.to_partner_id.id):
                raise except_orm(u'错误', u'转出客户和转入客户不能相同')

            # 核销预收预付
            for line in order.advance_payment_ids:
                order_reconcile += line.this_reconcile
                if line.this_reconcile > line.to_reconcile:
                    raise except_orm(u'错误', u'核销金额不能大于未核销金额')

                # 更新每一行的已核销余额、未核销余额
                line.name.to_reconcile -= line.this_reconcile
                line.name.reconciled += line.this_reconcile

            for line in order.receivable_source_ids:
                invoice_reconcile += line.this_reconcile
                self._get_or_pay(line, order.business_type,
                                 order.partner_id,
                                 order.to_partner_id, order.name)
            for line in order.payable_source_ids:
                if self.business_type == 'adv_get_to_pay':
                    invoice_reconcile += line.this_reconcile
                else:
                    order_reconcile += line.this_reconcile
                self._get_or_pay(line, order.business_type,
                                 order.partner_id,
                                 order.to_partner_id, order.name)

            # 核销金额必须相同
            if self.business_type in ['adv_pay_to_get',
                                      'adv_get_to_pay', 'get_to_pay']:
                if order_reconcile != invoice_reconcile:
                    raise except_orm(u'错误', u'核销金额必须相同, %s 不等于 %s' % (order_reconcile, invoice_reconcile))

            order.state = 'done'
        return True


class advance_payment(models.Model):
    _name = 'advance.payment'
    _description = u'核销单预收付款行'

    pay_reconcile_id = fields.Many2one('reconcile.order', string=u'核销单')
    name = fields.Many2one('money.order', string=u'预付款单编号',
                           copy=False, required=True)
    date = fields.Date(string=u'单据日期')
    amount = fields.Float(string=u'单据金额')
    reconciled = fields.Float(string=u'已核销金额')
    to_reconcile = fields.Float(string=u'未核销金额')
    this_reconcile = fields.Float(string=u'本次核销金额')


class cost_line(models.Model):
    _name = 'cost.line'
    _description = u"采购销售费用"

    partner_id = fields.Many2one('partner', u'供应商')
    category_id = fields.Many2one('core.category', u'类别',
                                  domain="[('type', '=', 'other_pay')]")
    amount = fields.Float(u'金额')
    note = fields.Char(u'备注')
