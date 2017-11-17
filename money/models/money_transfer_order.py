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


class MoneyTransferOrder(models.Model):
    _name = 'money.transfer.order'
    _description = u'资金转账单'
    _inherit = ['mail.thread']

    state = fields.Selection([
        ('draft', u'未审核'),
        ('done', u'已审核'),
        ('cancel', u'已作废'),
    ], string=u'状态', readonly=True,
        default='draft', copy=False, index=True,
        help=u'资金转账单状态标识，新建时状态为未审核;审核后状态为已审核')
    name = fields.Char(string=u'单据编号', copy=False, default='/',
                       help=u'单据编号，创建时会自动生成')
    date = fields.Date(string=u'单据日期', readonly=True,
                       default=lambda self: fields.Date.context_today(self),
                       states={'draft': [('readonly', False)]},
                       help=u'单据创建日期')
    note = fields.Text(string=u'备注', help=u'可以为该单据添加一些需要的标识信息')
    line_ids = fields.One2many('money.transfer.order.line', 'transfer_id',
                               string=u'资金转账单行', readonly=True,
                               states={'draft': [('readonly', False)]},
                               help=u'资金转账单明细行')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    voucher_id = fields.Many2one('voucher',
                                 u'对应凭证',
                                 readonly=True,
                                 ondelete='restrict',
                                 help=u'资金转账单审核时生成的对应凭证',
                                 copy=False)
    transfer_amount = fields.Float(
        compute='_compute_transfer_amount', string='转账总金额')

    @api.one
    @api.depends('line_ids', 'line_ids.amount')
    def _compute_transfer_amount(self):
        self.transfer_amount = sum([line.amount for line in self.line_ids])

    @api.multi
    def money_transfer_done(self):
        '''转账单的审核按钮'''
        self.ensure_one()
        if not self.line_ids:
            raise UserError('请先输入转账金额')
        decimal_amount = self.env.ref('core.decimal_amount')
        for line in self.line_ids:
            company_currency_id = self.env.user.company_id.currency_id.id
            out_currency_id = line.out_bank_id.account_id.currency_id.id or company_currency_id
            in_currency_id = line.in_bank_id.account_id.currency_id.id or company_currency_id

            if line.out_bank_id == line.in_bank_id:
                raise UserError('转出账户与转入账户不能相同')
            if line.amount <= 0:
                raise UserError('转账金额必须大于0。\n 转账金额:%s' % line.amount)
            if out_currency_id == company_currency_id:  # 如果转出账户是公司本位币
                if float_compare(line.out_bank_id.balance, line.amount, decimal_amount.digits) == -1:
                    raise UserError('转出账户余额不足。\n转出账户余额:%s 本次转出金额:%s' % (
                        line.out_bank_id.balance, line.amount))
                else:   # 转出账户余额充足
                    line.out_bank_id.balance -= line.amount
                if in_currency_id == company_currency_id:   # 如果转入账户是公司本位币
                    line.in_bank_id.balance += line.amount
                else:   # 如果转入账户是外币
                    line.in_bank_id.balance += line.currency_amount
            else:   # 如果转出账户是外币
                if float_compare(line.out_bank_id.balance, line.currency_amount, precision_digits=decimal_amount.digits) == -1:
                    raise UserError('转出账户余额不足。\n转出账户余额:%s 本次转出外币金额:%s'
                                    % (line.out_bank_id.balance, line.currency_amount))
                if in_currency_id == company_currency_id:   # 如果转入账户是公司本位币
                    line.in_bank_id.balance += line.amount
                    line.out_bank_id.balance -= line.currency_amount
                else:   # 如果转入账户是外币
                    raise UserError('系统不支持外币转外币')

        # 创建凭证并审核
        voucher = self.create_voucher()
        return self.write({
            'voucher_id': voucher.id,
            'state': 'done',
        })

    @api.multi
    def money_transfer_draft(self):
        '''转账单的反审核按钮,外币要考虑是转入还是转出'''
        self.ensure_one()
        decimal_amount = self.env.ref('core.decimal_amount')
        for line in self.line_ids:
            if line.currency_amount > 0:
                if line.in_bank_id.currency_id:  # 如果填充了转入账户的币别，则说明转入账户为外币
                    if float_compare(line.in_bank_id.balance, line.currency_amount, precision_digits=decimal_amount.digits) == -1:
                        raise UserError('转入账户余额不足。\n转入账户余额:%s 本次转出外币金额:%s'
                                        % (line.in_bank_id.balance, line.currency_amount))
                    else:   # 转入账户余额充足
                        line.in_bank_id.balance -= line.currency_amount
                        line.out_bank_id.balance += line.amount
                else:   # 转入账户为本位币
                    if float_compare(line.in_bank_id.balance, line.amount, precision_digits=decimal_amount.digits) == -1:
                        raise UserError('转入账户余额不足。\n转入账户余额:%s 本次转出金额:%s'
                                        % (line.in_bank_id.balance, line.amount))
                    else:
                        line.in_bank_id.balance -= line.amount
                        line.out_bank_id.balance += line.currency_amount
            else:   # 转入/转出账户都为本位币
                if float_compare(line.in_bank_id.balance, line.amount, precision_digits=decimal_amount.digits) == -1:
                    raise UserError('转入账户余额不足。\n转入账户余额:%s 本次转出金额:%s'
                                    % (line.in_bank_id.balance, line.amount))
                else:
                    line.in_bank_id.balance -= line.amount
                    line.out_bank_id.balance += line.amount

        voucher = self.voucher_id
        self.write({
            'voucher_id': False,
            'state': 'draft',
        })
        # 反审核凭证并删除
        if voucher.state == 'done':
            voucher.voucher_draft()
        return True

    @api.multi
    def create_voucher(self):
        """创建凭证并审核"""
        vouch_obj = self.env['voucher'].create({'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        vals = {}
        for line in self.line_ids:
            out_currency_id = line.out_bank_id.account_id.currency_id.id or self.env.user.company_id.currency_id.id
            in_currency_id = line.in_bank_id.account_id.currency_id.id or self.env.user.company_id.currency_id.id
            company_currency_id = self.env.user.company_id.currency_id.id
            if (
                    out_currency_id != company_currency_id or in_currency_id != company_currency_id) and not line.currency_amount:
                raise UserError(u'错误' u'请请输入外币金额。')
            if line.currency_amount and out_currency_id != company_currency_id:
                '''结汇'''
                '''借方行'''
                self.env['voucher.line'].create({
                    'name': u"%s %s结汇至%s %s" % (self.name, line.out_bank_id.name, line.in_bank_id.name, self.note),
                    'account_id': line.in_bank_id.account_id.id, 'debit': line.amount,
                    'voucher_id': vouch_obj.id, 'partner_id': '', 'currency_id': '',
                })
                '''贷方行'''
                self.env['voucher.line'].create({
                    'name': u"%s %s结汇至%s %s" % (self.name, line.out_bank_id.name, line.in_bank_id.name, self.note),
                    'account_id': line.out_bank_id.account_id.id, 'credit': line.amount,
                    'voucher_id': vouch_obj.id, 'partner_id': '', 'currency_id': out_currency_id,
                    'currency_amount': line.currency_amount, 'rate_silent': line.amount / line.currency_amount
                })
            elif line.currency_amount and in_currency_id != company_currency_id:
                '''买汇'''
                '''借方行'''
                self.env['voucher.line'].create({
                    'name': u"%s %s买汇至%s %s" % (self.name, line.out_bank_id.name, line.in_bank_id.name, self.note),
                    'account_id': line.in_bank_id.account_id.id, 'debit': line.amount,
                    'voucher_id': vouch_obj.id, 'partner_id': '', 'currency_id': in_currency_id,
                    'currency_amount': line.currency_amount, 'rate_silent': line.amount / line.currency_amount
                })
                '''贷方行'''
                self.env['voucher.line'].create({
                    'name': u"%s %s买汇至%s %s" % (self.name, line.out_bank_id.name, line.in_bank_id.name, self.note),
                    'account_id': line.out_bank_id.account_id.id, 'credit': line.amount,
                    'voucher_id': vouch_obj.id, 'partner_id': '', 'currency_id': '',
                })
            else:
                '''人民币间'''
                vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'string': self.note or '',
                             'amount': abs(line.amount), 'credit_account_id': line.out_bank_id.account_id.id,
                             'debit_account_id': line.in_bank_id.account_id.id,
                             })
                self.env['money.invoice'].create_voucher_line(vals)

        vouch_obj.voucher_done()
        return vouch_obj


class MoneyTransferOrderLine(models.Model):
    _name = 'money.transfer.order.line'
    _description = u'资金转账单明细'

    transfer_id = fields.Many2one('money.transfer.order',
                                  string=u'资金转账单', ondelete='cascade',
                                  help=u'资金转账单行对应的资金转账单')
    out_bank_id = fields.Many2one('bank.account', string=u'转出账户',
                                  required=True, ondelete='restrict',
                                  help=u'资金转账单行上的转出账户')
    in_bank_id = fields.Many2one('bank.account', string=u'转入账户',
                                 required=True, ondelete='restrict',
                                 help=u'资金转账单行上的转入账户')
    currency_amount = fields.Float(string=u'外币金额',
                                   digits=dp.get_precision('Amount'),
                                   help=u'转出或转入的外币金额')
    amount = fields.Float(string=u'金额',
                          digits=dp.get_precision('Amount'),
                          help=u'转出或转入的金额')
    mode_id = fields.Many2one('settle.mode', string=u'结算方式',
                              ondelete='restrict',
                              help=u'结算方式：支票、信用卡等')
    number = fields.Char(string=u'结算号', help=u'本次结算号')
    note = fields.Char(string=u'备注',
                       help=u'可以为该单据添加一些需要的标识信息')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
