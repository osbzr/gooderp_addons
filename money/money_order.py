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

from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from odoo import fields, models, api
from odoo.tools import float_compare, float_is_zero

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
        if  self.env.context.get('type') == 'pay':
            values.update({'name': self.env['ir.sequence'].next_by_code('pay.order')})
        else:
            values.update({'name': self.env['ir.sequence'].next_by_code('get.order')})

        # 创建时查找该业务伙伴是否存在 未审核 状态下的收付款单
        orders = self.env['money.order'].search([('partner_id', '=', values.get('partner_id')),
                                                 ('state', '=', 'draft'),
                                                 ('id', '!=', self.id)])
        if orders:
            raise UserError(u'该业务伙伴存在未审核的收/付款单，请先审核')

        return super(money_order, self).create(values)

    @api.multi
    def write(self, values):
        # 保存时查找该业务伙伴是否存在 未审核 状态下的收付款单
        if values.get('partner_id'):
            orders = self.env['money.order'].search([('partner_id', '=', values.get('partner_id')),
                                                     ('state', '=', 'draft'),
                                                     ('id', '!=', self.id)])
            if orders:
                raise UserError(u'业务伙伴(%s)存在未审核的收/付款单，请先审核'%orders.partner_id.name)

        return super(money_order, self).write(values)

    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise UserError(u'不可以删除已经审核的单据')

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

        if self.type == 'get':
            self.advance_payment = amount - this_reconcile + self.discount_amount
        else:
            self.advance_payment = amount - this_reconcile - self.discount_amount

        self.amount = amount

    @api.one
    @api.depends('partner_id')
    def _compute_currency_id(self):
        partner_currency_id = self.partner_id.c_category_id.account_id.currency_id.id or self.partner_id.s_category_id.account_id.currency_id.id
        self.currency_id = partner_currency_id or self.env.user.company_id.currency_id.id


    state = fields.Selection([
                          ('draft', u'未审核'),
                          ('done', u'已审核'),
                          ], string=u'状态', readonly=True,
                             default='draft', copy=False,
                        help=u'收付款单状态标识，新建时状态为未审核;审核后状态为已审核')
    partner_id = fields.Many2one('partner', string=u'业务伙伴', required=True,
                                 readonly=True, ondelete='restrict',
                                 states={'draft': [('readonly', False)]},
                                help=u'该单据对应的业务伙伴，单据审核时会影响他的应收应付余额')
    date = fields.Date(string=u'单据日期', readonly=True,
                       default=lambda self: fields.Date.context_today(self),
                       states={'draft': [('readonly', False)]},
                       help=u'单据创建日期')
    name = fields.Char(string=u'单据编号', copy=False, readonly=True,
                       help=u'单据编号，创建时会根据类型自动生成')
    note = fields.Text(string=u'备注', help=u'可以为该单据添加一些需要的标识信息')
    currency_id = fields.Many2one('res.currency', u'外币币别',
                                  compute='_compute_currency_id', store=True, readonly=True,
                                  help=u'业务伙伴的类别科目上对应的外币币别')
    discount_amount = fields.Float(string=u'手续费/折扣', readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   digits=dp.get_precision('Amount'),
                                   help=u'收款时发生的银行手续费或付款时给供应商的现金折扣。')
    discount_account_id = fields.Many2one('finance.account', u'费用科目',
                                          readonly=True,
                                          states={'draft': [('readonly', False)]},
                                          help=u'收付款单审核生成凭证时，手续费或折扣对应的科目')
    line_ids = fields.One2many('money.order.line', 'money_id',
                               string=u'收付款单行', readonly=True,
                               states={'draft': [('readonly', False)]},
                               help=u'收付款单明细行')
    source_ids = fields.One2many('source.order.line', 'money_id',
                                 string=u'结算单行', readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 help=u'收付款单原始单据行')
    type = fields.Selection(TYPE_SELECTION, string=u'类型',
                            default=lambda self: self.env.context.get('type'),
                            help=u'类型：收款单 或者 付款单')
    amount = fields.Float(string=u'总金额', compute='_compute_advance_payment',
                          digits=dp.get_precision('Amount'),
                          store=True, readonly=True,
                          help=u'收付款单行金额总和')
    advance_payment = fields.Float(string=u'本次预收/付款',
                                   compute='_compute_advance_payment',
                                   digits=dp.get_precision('Amount'),
                                   store=True, readonly=True,
                                   help=u'根据收付款单行金额总和，原始单据行金额总和及折扣额计算得来的预收/预付款，'
                                        u'值>=0')
    to_reconcile = fields.Float(string=u'未核销预收款',
                                digits=dp.get_precision('Amount'),
                            help=u'未核销的预收/预付款金额')
    reconciled = fields.Float(string=u'已核销预收款',
                              digits=dp.get_precision('Amount'),
                            help=u'已核销的预收/预付款金额')
    origin_name = fields.Char(u'原始单据编号',
                            help=u'原始单据编号')
    bank_name = fields.Char(u'开户行',
                            help=u'开户行取自业务伙伴，可修改')
    bank_num = fields.Char(u'银行账号',
                            help=u'银行账号取自业务伙伴，可修改')

    @api.onchange('date')
    def onchange_date(self):
        if  self.env.context.get('type') == 'get':
            return {'domain': {'partner_id': [('c_category_id', '!=', False)]}}
        else:
            return {'domain': {'partner_id': [('s_category_id', '!=', False)]}}

    def _get_source_line(self, invoice):
        return {
                'name': invoice.id,
                'category_id': invoice.category_id.id,
                'amount': invoice.amount,
                'date': invoice.date,
                'reconciled': invoice.reconciled,
                'to_reconcile': invoice.to_reconcile,
                'this_reconcile': invoice.to_reconcile,
                'date_due': invoice.date_due,
                }

    def _get_invoice_search_list(self):
        invoice_search_list = [('partner_id', '=', self.partner_id.id),
                               ('to_reconcile', '!=', 0)]
        if self.env.context.get('type') == 'get':
            invoice_search_list.append(('category_id.type', '=', 'income'))
        else: # type = 'pay':
            invoice_search_list.append(('category_id.type', '=', 'expense'))

        return invoice_search_list

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            return {}

        source_lines = []
        self.bank_name = self.partner_id.bank_name
        self.bank_num = self.partner_id.bank_num

        for invoice in self.env['money.invoice'].search(self._get_invoice_search_list()):
            source_lines.append(self._get_source_line(invoice))
        if source_lines:
            self.source_ids = source_lines

    @api.multi
    def money_order_done(self):
        '''对收支单的审核按钮'''
        for order in self:
            if order.type == 'pay' and not order.partner_id.s_category_id.account_id:
                raise UserError(u'请输入供应商类别(%s)上的科目'%order.partner_id.s_category_id.name)
            if order.type == 'get' and not order.partner_id.c_category_id.account_id:
                raise UserError(u'请输入客户类别(%s)上的科目'%order.partner_id.c_category_id.name)
            if order.advance_payment < 0:
                raise UserError(u'本次核销金额不能大于付款金额!\n差额: %s'%(order.advance_payment))

            order.to_reconcile = order.advance_payment
            order.reconciled = order.amount - order.advance_payment

            total = 0
            for line in order.line_ids:
                if order.type == 'pay':  # 付款账号余额减少, 退款账号余额增加
                    decimal_amount = self.env.ref('core.decimal_amount')
                    if float_compare(line.bank_id.balance, line.amount, precision_digits=decimal_amount.digits) == -1:
                        raise UserError(u'账户余额不足!\n账户余额:%s 订单金额:%s'%(line.bank_id.balance,line.amount))
                    line.bank_id.balance -= line.amount
                else:  # 收款账号余额增加, 退款账号余额减少
                    line.bank_id.balance += line.amount
                total += line.amount

            if order.type == 'pay':
                order.partner_id.payable -= total - self.discount_amount
            else:
                order.partner_id.receivable -= total + self.discount_amount

            # 更新结算单的未核销金额、已核销金额
            for source in order.source_ids:
                '''float_compare(value1,value2): return -1, 0 or 1,
                if 'value1' is lower than, equal to, or greater than 'value2' at the given precision'''
                decimal_amount = self.env.ref('core.decimal_amount')
                if float_compare(source.this_reconcile, abs(source.to_reconcile), precision_digits=decimal_amount.digits) == 1:
                    raise UserError(u'本次核销金额不能大于未核销金额!\n 核销金额:%s 未核销金额:%s'
                                    %(abs(source.to_reconcile),source.this_reconcile))

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
                if order.type == 'pay':  # 反审核：付款账号余额增加
                    line.bank_id.balance += line.amount
                else:  # 反审核：收款账号余额减少
                    decimal_amount = self.env.ref('core.decimal_amount')
                    if float_compare(line.bank_id.balance, line.amount, precision_digits=decimal_amount.digits) == -1:
                        raise UserError(u'账户余额不足!\n 账户余额:%s 订单金额:%s' % (line.bank_id.balance, line.amount))
                    line.bank_id.balance -= line.amount
                total += line.amount

            if order.type == 'pay':
                order.partner_id.payable += total - self.discount_amount
            else:
                order.partner_id.receivable += total + self.discount_amount

            for source in order.source_ids:
                source.name.to_reconcile = (source.to_reconcile + 
                                            source.this_reconcile)
                source.name.reconciled = (source.reconciled - 
                                          source.this_reconcile)

            order.state = 'draft'
        return True


class money_order_line(models.Model):
    _name = 'money.order.line'
    _description = u'收付款单明细'

    @api.one
    @api.depends('bank_id')
    def _compute_currency_id(self):
        partner_currency_id = self.bank_id.account_id.currency_id.id or self.env.user.company_id.currency_id.id
        self.currency_id = partner_currency_id or self.env.user.company_id.currency_id.id
        if self.bank_id and self.currency_id.id != self.money_id.currency_id.id :
            raise ValidationError(u'结算帐户与业务伙伴币别不一致\n 结算账户币别:%s 业务伙伴币别:%s'
                                  %(self.currency_id.name,self.money_id.currency_id.name))

    money_id = fields.Many2one('money.order', string=u'收付款单',
                               ondelete='cascade',
                            help=u'订单行对应的收付款单')
    bank_id = fields.Many2one('bank.account', string=u'结算账户',
                              required=True, ondelete='restrict',
                            help=u'本次收款/付款所用的计算账户，审核收付款单会修改对应账户的金额')
    amount = fields.Float(string=u'金额',
                          digits=dp.get_precision('Amount'),
                            help=u'本次结算金额')
    mode_id = fields.Many2one('settle.mode', string=u'结算方式',
                              ondelete='restrict',
                            help=u'结算方式：支票、信用卡等')
    currency_id = fields.Many2one('res.currency', u'外币币别', compute='_compute_currency_id',
                                  store=True, readonly=True,
                                  help=u'结算账户对应的外币币别')
    number = fields.Char(string=u'结算号',
                                  help=u'本次结算号')
    note = fields.Char(string=u'备注',
                       help=u'可以为本次结算添加一些需要的标识信息')


class money_invoice(models.Model):
    _name = 'money.invoice'
    _description = u'结算单'
    # _rec_name = 'bill_number'

    @api.multi
    def name_get(self):
        '''在many2one字段里显示 名称_票号'''
        res = []

        for invoice in self:
            res.append((invoice.id, invoice.bill_number and invoice.bill_number or invoice.name))
        return res

    state = fields.Selection([
                          ('draft', u'草稿'),
                          ('done', u'完成')
                          ], string=u'状态', readonly=True,
                          default='draft', copy=False,
                        help=u'结算单状态标识，新建时状态为草稿;审核后状态为完成')
    partner_id = fields.Many2one('partner', string=u'业务伙伴',
                                 required=True, readonly=True,
                                 ondelete='restrict',
                                 help=u'该单据对应的业务伙伴')
    name = fields.Char(string=u'订单编号', copy=False,
                       readonly=True, required=True,
                       help=u'该结算单编号，取自生成结算单的采购入库单和销售入库单')
    category_id = fields.Many2one('core.category', string=u'类别',
                                  readonly=True, ondelete='restrict',
                                  help=u'结算单类别：采购 或者 销售等')
    date = fields.Date(string=u'单据日期', readonly=True,
                       default=lambda self: fields.Date.context_today(self),
                       help=u'单据创建日期')
    amount = fields.Float(string=u'单据金额', readonly=True,
                          digits=dp.get_precision('Amount'),
                          help=u'原始单据对应金额')
    reconciled = fields.Float(string=u'已核销金额', readonly=True,
                              digits=dp.get_precision('Amount'),
                              help=u'原始单据已核销掉的金额')
    to_reconcile = fields.Float(string=u'未核销金额', readonly=True,
                                digits=dp.get_precision('Amount'),
                                help=u'原始单据未核销掉的金额')
    tax_amount = fields.Float(u'税额', readonly=True,
                              digits=dp.get_precision('Amount'),
                              help=u'对应税额')

    auxiliary_id = fields.Many2one('auxiliary.financing', u'辅助核算',
                                   help=u'辅助核算')
    date_due = fields.Date(string=u'到期日',
                           help=u'结算单的到期日')
    currency_id = fields.Many2one('res.currency', u'外币币别', readonly=True,
                                  help=u'原始单据对应的外币币别')
    bill_number = fields.Char(u'发票号',
                              help=u'结算单对应的会计凭证号')
    is_init = fields.Boolean(u'是否初始化单')

    @api.multi
    def money_invoice_done(self):
        for inv in self:
            inv.state = 'done'
            if inv.category_id.type == 'income':
                inv.partner_id.receivable += inv.amount
            if inv.category_id.type == 'expense':
                inv.partner_id.payable += inv.amount

    @api.multi
    def money_invoice_draft(self):
        for inv in self:
            inv.state = 'draft'
            if inv.category_id.type == 'income':
                inv.partner_id.receivable -= inv.amount
            if inv.category_id.type == 'expense':
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
                raise UserError(u'不可以删除已经审核的单据')

        return super(money_invoice, self).unlink()

    @api.multi
    def find_source_order(self):
        # 查看原始单据，四情况：销售发货单、销售退货单、采购退货单、采购入库单、项目、委外加工单等
        self.ensure_one()
        # FIXME: 判断
        sell = self.env['sell.delivery'].search([('name', '=', self.name)])
        if sell:
            view = (not sell.is_return
                   and self.env.ref('sell.sell_delivery_form')
                   or self.env.ref('sell.sell_return_form'))
            name = (not sell.is_return and u'销售发货单' or u'销售退货单')
            return {
                'name': name,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'sell.delivery',
                'type': 'ir.actions.act_window',
                'res_id': sell.id,
            }
        buy = self.env['buy.receipt'].search([('name', '=', self.name)])
        if buy:
            view = (not buy.is_return
                   and self.env.ref('buy.buy_receipt_form')
                   or self.env.ref('buy.buy_return_form'))
            name = (not buy.is_return and u'采购入库单' or u'采购退货单')
            return {
                'name': name,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'buy.receipt',
                'type': 'ir.actions.act_window',
                'res_id': buy.id,
            }
        project = self.env['project'].search([('name', '=', self.name)])
        if project:
            view = self.env.ref('task.project_form')
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'project',
                'type': 'ir.actions.act_window',
                'res_id': project.id,
            }
        outsource = self.env['outsource'].search([('name', '=', self.name)])
        if outsource:
            view = self.env.ref('warehouse.outsource_form')
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'outsource',
                'type': 'ir.actions.act_window',
                'res_id': outsource.id,
            }
        raise UserError(u'期初余额没有原始单据可供查看！')


class source_order_line(models.Model):
    _name = 'source.order.line'
    _description = u'结算单明细'

    money_id = fields.Many2one('money.order', string=u'收付款单',
                               ondelete='cascade',
                                help=u'原始单据行对应的收付款单')  # 收付款单上的结算单明细
    receivable_reconcile_id = fields.Many2one('reconcile.order',
                            string=u'核销单', ondelete='cascade',
                            help=u'核销单上的应收结算单明细')  # 核销单上的应收结算单明细
    payable_reconcile_id = fields.Many2one('reconcile.order',
                            string=u'核销单', ondelete='cascade',
                            help=u'核销单上的应付结算单明细')  # 核销单上的应付结算单明细
    name = fields.Many2one('money.invoice', string=u'结算单编号',
                           copy=False, required=True,
                           ondelete='cascade',
                           help=u'原始单据行对应的结算单编号')
    category_id = fields.Many2one('core.category', string=u'类别',
                                  required=True, ondelete='restrict',
                                  help=u'原始单据行类别：采购 或者 销售等')
    date = fields.Date(string=u'单据日期',
                       help=u'单据创建日期')
    amount = fields.Float(string=u'单据金额',
                        digits=dp.get_precision('Amount'),
                        help=u'原始单据对应金额')
    reconciled = fields.Float(string=u'已核销金额',
                        digits=dp.get_precision('Amount'),
                        help=u'原始单据已核销掉的金额')
    to_reconcile = fields.Float(string=u'未核销金额',
                        digits=dp.get_precision('Amount'),
                        help=u'原始单据未核销掉的金额')
    this_reconcile = fields.Float(string=u'本次核销金额',
                        digits=dp.get_precision('Amount'),
                        help=u'本次要核销掉的金额')
    date_due = fields.Date(string=u'到期日',
                           help=u'原始单据的到期日')


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
            values.update({'name': self.env['ir.sequence'].next_by_code(self._name)})

        return super(reconcile_order, self).create(values)

    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise UserError(u'不可以删除已经审核的单据')

        return super(reconcile_order, self).unlink()

    state = fields.Selection([
                          ('draft', u'未审核'),
                          ('done', u'已审核'),
                          ], string=u'状态', readonly=True,
                          default='draft', copy=False,
                        help=u'核销单状态标识，新建时状态为未审核;审核后状态为已审核')
    partner_id = fields.Many2one('partner', string=u'业务伙伴', required=True,
                                 readonly=True, ondelete='restrict',
                                 states={'draft': [('readonly', False)]},
                                 help=u'该单据对应的业务伙伴，与业务类型一起带出待核销的明细行')
    to_partner_id = fields.Many2one('partner', string=u'转入往来单位',
                                    readonly=True, ondelete='restrict',
                                    states={'draft': [('readonly', False)]},
                                help=u'应收转应收、应付转应付时对应的转入业务伙伴，'
                                       u'订单审核时会影响该业务伙伴的应收/应付')
    advance_payment_ids = fields.One2many(
                            'advance.payment', 'pay_reconcile_id',
                            string=u'预收单行', readonly=True,
                            states={'draft': [('readonly', False)]},
                            help=u'业务伙伴有预付款单，自动带出，用来与应收/应付款单核销')
    receivable_source_ids = fields.One2many(
                            'source.order.line', 'receivable_reconcile_id',
                             string=u'应收结算单行', readonly=True,
                             states={'draft': [('readonly', False)]},
                            help=u'业务伙伴有应收结算单，自动带出，待与预收款单核销')
    payable_source_ids = fields.One2many(
                            'source.order.line', 'payable_reconcile_id',
                            string=u'应付结算单行', readonly=True,
                            states={'draft': [('readonly', False)]},
                            help=u'业务伙伴有应付结算单，自动带出，待与预付款单核销')
    business_type = fields.Selection(TYPE_SELECTION, string=u'业务类型',
                                     readonly=True,
                                     states={'draft': [('readonly', False)]},
                                     help=u'类型：预收冲应收,预付冲应付,应收冲应付,应收转应收,应付转应付'
                                     )
    name = fields.Char(string=u'单据编号', copy=False, readonly=True, default='/',
                       help=u'单据编号，创建时会自动生成')
    date = fields.Date(string=u'单据日期', readonly=True,
                       default=lambda self: fields.Date.context_today(self),
                       states={'draft': [('readonly', False)]},
                       help=u'单据创建日期')
    note = fields.Text(string=u'备注',
                       help=u'可以为该单据添加一些需要的标识信息')

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
        decimal_amount = self.env.ref('core.decimal_amount')
        if float_compare(line.this_reconcile, line.to_reconcile, precision_digits=decimal_amount.digits) == 1:
            raise UserError(u'核销金额不能大于未核销金额!\n核销金额:%s 未核销金额:%s'%(line.this_reconcile, line.to_reconcile))
        # 更新每一行的已核销余额、未核销余额
        line.name.to_reconcile -= line.this_reconcile
        line.name.reconciled += line.this_reconcile

        # 应收转应收、应付转应付
        if business_type in ['get_to_get', 'pay_to_pay']:
            if not float_is_zero(line.this_reconcile, 2):
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
#                 to_partner_id.receivable += line.this_reconcile
                partner_id.receivable -= line.this_reconcile
            if business_type == 'pay_to_pay':
#                 to_partner_id.payable += line.this_reconcile
                partner_id.payable -= line.this_reconcile

        return True

    @api.multi
    def reconcile_order_done(self):
        '''核销单的审核按钮'''
        # 核销金额不能大于未核销金额
        for order in self:
            if order.state == 'done':
                raise UserError(u'核销单%s已审核，不能再次审核' % order.name)
            order_reconcile, invoice_reconcile = 0, 0
            if self.business_type in ['get_to_get', 'pay_to_pay'] and order.partner_id == order.to_partner_id:
                raise UserError(u'转出客户和转入客户不能相同!\n转出客户:%s 转入客户:%s'
                                %(order.partner_id.name, order.to_partner_id.name))

            # 核销预收预付
            for line in order.advance_payment_ids:
                order_reconcile += line.this_reconcile
                decimal_amount = self.env.ref('core.decimal_amount')
                if float_compare(line.this_reconcile, line.to_reconcile, precision_digits=decimal_amount.digits) == 1:
                    raise UserError(u'核销金额不能大于未核销金额\n核销金额:%s 未核销金额:%s'%(line.this_reconcile, line.to_reconcile))

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
                decimal_amount = self.env.ref('core.decimal_amount')
                if float_compare(order_reconcile, invoice_reconcile, precision_digits=decimal_amount.digits) != 0:
                    raise UserError(u'核销金额必须相同, %s 不等于 %s'
                                     % (order_reconcile, invoice_reconcile))

            order.state = 'done'
        return True


class advance_payment(models.Model):
    _name = 'advance.payment'
    _description = u'核销单预收付款行'

    pay_reconcile_id = fields.Many2one('reconcile.order',
                            string=u'核销单', ondelete='cascade',
                            help=u'核销单预收付款行对应的核销单')
    name = fields.Many2one('money.order', string=u'预付款单编号',
                    copy=False, required=True, ondelete='cascade',
                    help=u'核销单预收付款行对应的预付款单编号')
    date = fields.Date(string=u'单据日期',
                       help=u'单据创建日期')
    amount = fields.Float(string=u'单据金额',
                        digits=dp.get_precision('Amount'),
                        help=u'预收付款单的预收金额')
    reconciled = fields.Float(string=u'已核销金额',
                        digits=dp.get_precision('Amount'),
                        help=u'已核销的预收/预付款金额')
    to_reconcile = fields.Float(string=u'未核销金额',
                        digits=dp.get_precision('Amount'),
                        help=u'未核销的预收/预付款金额')
    this_reconcile = fields.Float(string=u'本次核销金额',
                        digits=dp.get_precision('Amount'),
                        help=u'本次核销的预收/预付款金额')


class cost_line(models.Model):
    _name = 'cost.line'
    _description = u"采购销售费用"

    @api.one
    @api.depends('amount', 'tax_rate')
    def _compute_tax(self):
        self.tax = self.amount * self.tax_rate * 0.01

    partner_id = fields.Many2one('partner', u'供应商', ondelete='restrict',
                                 required=True,
                                 help=u'采购/销售费用对应的业务伙伴')
    category_id = fields.Many2one('core.category', u'类别',
                                  required=True,
                                  ondelete='restrict',
                                  help=u'分类：其他支出')
    amount = fields.Float(u'金额',
                          required=True,
                          digits=dp.get_precision('Amount'),
                          help=u'采购/销售费用金额')
    tax_rate = fields.Float(u'税率(%)',
                            default=lambda self:self.env.user.company_id.import_tax_rate,
                            help=u'默认值取公司进项税率')
    tax = fields.Float(u'税额',
                       digits=dp.get_precision('Amount'),
                       compute=_compute_tax,
                       help=u'采购/销售费用税额')
    note = fields.Char(u'备注',
                       help=u'该采购/销售费用添加的一些标识信息')
