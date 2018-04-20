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
from odoo.tools import float_compare


class OtherMoneyOrder(models.Model):
    _name = 'other.money.order'
    _description = u'其他收入/其他支出'
    _inherit = ['mail.thread']

    TYPE_SELECTION = [
        ('other_pay', u'其他支出'),
        ('other_get', u'其他收入'),
    ]

    @api.model
    def create(self, values):
        # 创建单据时，更新订单类型的不同，生成不同的单据编号
        if self.env.context.get('type') == 'other_get':
            values.update(
                {'name': self.env['ir.sequence'].next_by_code('other.get.order')})
        if self.env.context.get('type') == 'other_pay' or values.get('name', '/') == '/':
            values.update(
                {'name': self.env['ir.sequence'].next_by_code('other.pay.order')})

        return super(OtherMoneyOrder, self).create(values)

    @api.one
    @api.depends('line_ids.amount', 'line_ids.tax_amount')
    def _compute_total_amount(self):
        # 计算应付金额/应收金额
        self.total_amount = sum((line.amount + line.tax_amount)
                                for line in self.line_ids)

    state = fields.Selection([
        ('draft', u'草稿'),
        ('done', u'已确认'),
        ('cancel', u'已作废'),
    ], string=u'状态', readonly=True,
        default='draft', copy=False, index=True,
        help=u'其他收支单状态标识，新建时状态为草稿;确认后状态为已确认')
    partner_id = fields.Many2one('partner', string=u'往来单位',
                                 readonly=True, ondelete='restrict',
                                 states={'draft': [('readonly', False)]},
                                 help=u'单据对应的业务伙伴，单据确认时会影响他的应收应付余额')
    date = fields.Date(string=u'单据日期', readonly=True,
                       default=lambda self: fields.Date.context_today(self),
                       states={'draft': [('readonly', False)]},
                       copy=False,
                       help=u'单据创建日期')
    name = fields.Char(string=u'单据编号', copy=False, readonly=True, default='/',
                       help=u'单据编号，创建时会根据类型自动生成')
    total_amount = fields.Float(string=u'金额', compute='_compute_total_amount',
                                store=True, readonly=True,
                                digits=dp.get_precision('Amount'),
                                help=u'本次其他收支的总金额')
    bank_id = fields.Many2one('bank.account', string=u'结算账户',
                              required=True, ondelete='restrict',
                              readonly=True, states={
                                  'draft': [('readonly', False)]},
                              help=u'本次其他收支的结算账户')
    line_ids = fields.One2many('other.money.order.line', 'other_money_id',
                               string=u'收支单行', readonly=True,
                               copy=True,
                               states={'draft': [('readonly', False)]},
                               help=u'其他收支单明细行')
    type = fields.Selection(TYPE_SELECTION, string=u'类型', readonly=True,
                            default=lambda self: self._context.get('type'),
                            states={'draft': [('readonly', False)]},
                            help=u'类型：其他收入 或者 其他支出')
    note = fields.Text(u'备注',
                       help=u'可以为该单据添加一些需要的标识信息')

    is_init = fields.Boolean(u'初始化应收应付', help=u'此单是否为初始化单')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    receiver = fields.Char(u'收款人',
                           help=u'收款人')
    bank_name = fields.Char(u'开户行')
    bank_num = fields.Char(u'银行账号')
    voucher_id = fields.Many2one('voucher',
                                 u'对应凭证',
                                 readonly=True,
                                 ondelete='restrict',
                                 copy=False,
                                 help=u'其他收支单确认时生成的对应凭证')
    currency_amount = fields.Float(u'外币金额',
                                   digits=dp.get_precision('Amount'))

    @api.onchange('date')
    def onchange_date(self):
        if self._context.get('type') == 'other_get':
            return {'domain': {'partner_id': [('c_category_id', '!=', False)]}}
        else:
            return {'domain': {'partner_id': [('s_category_id', '!=', False)]}}

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        更改业务伙伴，自动填入收款人、开户行和银行帐号
        """
        if self.partner_id:
            self.receiver = self.partner_id.name
            self.bank_name = self.partner_id.bank_name
            self.bank_num = self.partner_id.bank_num

    @api.multi
    def other_money_done(self):
        '''其他收支单的审核按钮'''
        self.ensure_one()
        if float_compare(self.total_amount, 0, 3) <= 0:
            raise UserError(u'金额应该大于0。\n金额:%s' % self.total_amount)
        if not self.bank_id.account_id:
            raise UserError(u'请配置%s的会计科目' % (self.bank_id.name))

        # 根据单据类型更新账户余额
        if self.type == 'other_pay':
            decimal_amount = self.env.ref('core.decimal_amount')
            if float_compare(self.bank_id.balance, self.total_amount, decimal_amount.digits) == -1:
                raise UserError(u'账户余额不足。\n账户余额:%s 本次支出金额:%s' %
                                (self.bank_id.balance, self.total_amount))
            self.bank_id.balance -= self.total_amount
        else:
            self.bank_id.balance += self.total_amount

        # 创建凭证并审核非初始化凭证
        vouch_obj = self.create_voucher()
        return self.write({
            'voucher_id': vouch_obj.id,
            'state': 'done',
        })

    @api.multi
    def other_money_draft(self):
        '''其他收支单的反审核按钮'''
        self.ensure_one()
        # 根据单据类型更新账户余额
        if self.type == 'other_pay':
            self.bank_id.balance += self.total_amount
        else:
            decimal_amount = self.env.ref('core.decimal_amount')
            if float_compare(self.bank_id.balance, self.total_amount, decimal_amount.digits) == -1:
                raise UserError(u'账户余额不足。\n账户余额:%s 本次支出金额:%s' %
                                (self.bank_id.balance, self.total_amount))
            self.bank_id.balance -= self.total_amount

        voucher = self.voucher_id
        self.write({
            'voucher_id': False,
            'state': 'draft',
        })
        # 反审核凭证并删除
        if voucher.state == 'done':
            voucher.voucher_draft()
        # 始初化单反审核只删除明细行
        if self.is_init:
            vouch_obj = self.env['voucher'].search([('id', '=', voucher.id)])
            vouch_obj_lines = self.env['voucher.line'].search([
                ('voucher_id', '=', vouch_obj.id),
                ('account_id', '=', self.bank_id.account_id.id),
                ('init_obj', '=', 'other_money_order-%s' % (self.id))])
            for vouch_obj_line in vouch_obj_lines:
                vouch_obj_line.unlink()
        else:
            voucher.unlink()
        return True

    @api.multi
    def create_voucher(self):
        """创建凭证并审核非初始化凭证"""
        init_obj = ''
        # 初始化单的话，先找是否有初始化凭证，没有则新建一个
        if self.is_init:
            vouch_obj = self.env['voucher'].search([('is_init', '=', True)])
            if not vouch_obj:
                vouch_obj = self.env['voucher'].create({'date': self.date,
                                                        'is_init': True,
                                                        'ref': '%s,%s' % (self._name, self.id)})
        else:
            vouch_obj = self.env['voucher'].create({'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        if self.is_init:
            init_obj = 'other_money_order-%s' % (self.id)

        if self.type == 'other_get':  # 其他收入单
            self.other_get_create_voucher_line(vouch_obj, init_obj)
        else:  # 其他支出单
            self.other_pay_create_voucher_line(vouch_obj)

        # 如果非初始化单则审核
        if not self.is_init:
            vouch_obj.voucher_done()
        return vouch_obj

    def other_get_create_voucher_line(self, vouch_obj, init_obj):
        """
        其他收入单生成凭证明细行
        :param vouch_obj: 凭证
        :return:
        """
        vals = {}
        for line in self.line_ids:
            if not line.category_id.account_id:
                raise UserError(u'请配置%s的会计科目' % (line.category_id.name))

            rate_silent = self.env['res.currency'].get_rate_silent(
                self.date, self.bank_id.currency_id.id)
            vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'note': line.note or '',
                         'credit_auxiliary_id': line.auxiliary_id.id,
                         'amount': abs(line.amount + line.tax_amount),
                         'credit_account_id': line.category_id.account_id.id,
                         'debit_account_id': self.bank_id.account_id.id,
                         'partner_credit': self.partner_id.id, 'partner_debit': '',
                         'sell_tax_amount': line.tax_amount or 0,
                         'init_obj': init_obj,
                         'currency_id': self.bank_id.currency_id.id,
                         'currency_amount': self.currency_amount,
                         'rate_silent': rate_silent,
                         })
            # 贷方行
            if not init_obj:
                self.env['voucher.line'].create({
                    'name': u"%s %s" % (vals.get('name'), vals.get('note')),
                    'partner_id': vals.get('partner_credit', ''),
                    'account_id': vals.get('credit_account_id'),
                    'credit': line.amount,
                    'voucher_id': vals.get('vouch_obj_id'),
                    'auxiliary_id': vals.get('credit_auxiliary_id', False),
                })
            # 销项税行
            if vals.get('sell_tax_amount'):
                if not self.env.user.company_id.output_tax_account:
                    raise UserError(
                        u'您还没有配置公司的销项税科目。\n请通过"配置-->高级配置-->公司"菜单来设置销项税科目!')
                self.env['voucher.line'].create({
                    'name': u"%s %s" % (vals.get('name'), vals.get('note')),
                    'account_id': self.env.user.company_id.output_tax_account.id,
                    'credit': line.tax_amount or 0,
                    'voucher_id': vals.get('vouch_obj_id'),
                })
        # 借方行
        self.env['voucher.line'].create({
            'name': u"%s" % (vals.get('name')),
            'account_id': vals.get('debit_account_id'),
            'debit': self.total_amount,  # 借方和
            'voucher_id': vals.get('vouch_obj_id'),
            'partner_id': vals.get('partner_debit', ''),
            'auxiliary_id': vals.get('debit_auxiliary_id', False),
            'init_obj': vals.get('init_obj', False),
            'currency_id': vals.get('currency_id', False),
            'currency_amount': vals.get('currency_amount'),
            'rate_silent': vals.get('rate_silent'),
        })

    def other_pay_create_voucher_line(self, vouch_obj):
        """
        其他支出单生成凭证明细行
        :param vouch_obj: 凭证
        :return:
        """
        vals = {}
        for line in self.line_ids:
            if not line.category_id.account_id:
                raise UserError(u'请配置%s的会计科目' % (line.category_id.name))

            rate_silent = self.env['res.currency'].get_rate_silent(
                self.date, self.bank_id.currency_id.id)
            vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'note': line.note or '',
                         'debit_auxiliary_id': line.auxiliary_id.id,
                         'amount': abs(line.amount + line.tax_amount),
                         'credit_account_id': self.bank_id.account_id.id,
                         'debit_account_id': line.category_id.account_id.id, 'partner_credit': '',
                         'partner_debit': self.partner_id.id,
                         'buy_tax_amount': line.tax_amount or 0,
                         'currency_id': self.bank_id.currency_id.id,
                         'currency_amount': self.currency_amount,
                         'rate_silent': rate_silent,
                         })
            # 借方行
            self.env['voucher.line'].create({
                'name': u"%s %s " % (vals.get('name'), vals.get('note')),
                'account_id': vals.get('debit_account_id'),
                'debit': line.amount,
                'voucher_id': vals.get('vouch_obj_id'),
                'partner_id': vals.get('partner_debit', ''),
                'auxiliary_id': vals.get('debit_auxiliary_id', False),
                'init_obj': vals.get('init_obj', False),
            })
            # 进项税行
            if vals.get('buy_tax_amount'):
                if not self.env.user.company_id.import_tax_account:
                    raise UserError(u'请通过"配置-->高级配置-->公司"菜单来设置进项税科目')
                self.env['voucher.line'].create({
                    'name': u"%s %s" % (vals.get('name'), vals.get('note')),
                    'account_id': self.env.user.company_id.import_tax_account.id,
                    'debit': line.tax_amount or 0,
                    'voucher_id': vals.get('vouch_obj_id'),
                })
        # 贷方行
        self.env['voucher.line'].create({
            'name': u"%s" % (vals.get('name')),
            'partner_id': vals.get('partner_credit', ''),
            'account_id': vals.get('credit_account_id'),
            'credit': self.total_amount,  # 贷方和
            'voucher_id': vals.get('vouch_obj_id'),
            'auxiliary_id': vals.get('credit_auxiliary_id', False),
            'init_obj': vals.get('init_obj', False),
            'currency_id': vals.get('currency_id', False),
            'currency_amount': vals.get('currency_amount'),
            'rate_silent': vals.get('rate_silent'),
        })


class OtherMoneyOrderLine(models.Model):
    _name = 'other.money.order.line'
    _description = u'其他收支单明细'

    @api.onchange('service')
    def onchange_service(self):
        # 当选择了收支项后，则自动填充上类别和金额
        if self.env.context.get('order_type') == 'other_get':
            self.category_id = self.service.get_categ_id.id
        elif self.env.context.get('order_type') == 'other_pay':
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
                              help=u'其他收支单行上对应的收支项')
    category_id = fields.Many2one('core.category',
                                  u'类别', ondelete='restrict',
                                  help=u'类型：运费、咨询费等')
    auxiliary_id = fields.Many2one('auxiliary.financing', u'辅助核算',
                                   help=u'其他收支单行上的辅助核算')
    amount = fields.Float(u'金额',
                          digits=dp.get_precision('Amount'),
                          help=u'其他收支单行上的金额')
    tax_rate = fields.Float(u'税率(%)',
                            default=lambda self: self.env.user.company_id.import_tax_rate,
                            help=u'其他收支单行上的税率')
    tax_amount = fields.Float(u'税额',
                              digits=dp.get_precision('Amount'),
                              help=u'其他收支单行上的税额')
    note = fields.Char(u'备注',
                       help=u'可以为该单据添加一些需要的标识信息')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
