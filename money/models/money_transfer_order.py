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


class money_transfer_order(models.Model):
    _name = 'money.transfer.order'
    _description = u'资金转账单'
    _inherit = ['mail.thread']


    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise UserError(u'不可以删除已经审核的单据\n 资金转账单%s已审核'%order.name)

        return super(money_transfer_order, self).unlink()

    state = fields.Selection([
                          ('draft', u'未审核'),
                          ('done', u'已审核'),
                           ], string=u'状态', readonly=True,
                             default='draft', copy=False,
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
    discount_amount = fields.Float(string=u'折扣', readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   digits=dp.get_precision('Amount'),
                                   help=u'资金转换时，待抹去的零头数据')
    discount_account_id = fields.Many2one('finance.account', u'折扣科目', ondelete='restrict',
                                          readonly=True, states={'draft': [('readonly', False)]},
                                          help=u'资金转换单审核生成凭证时，折扣额对应的科目')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

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
                    raise UserError('转出账户余额不足。\n转出账户余额:%s 本次转出金额:%s'%(line.out_bank_id.balance, line.amount))
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

        self.state = 'done'
        return True

    @api.multi
    def money_transfer_draft(self):
        '''转账单的反审核按钮,外币要考虑是转入还是转出'''
        self.ensure_one()
        decimal_amount = self.env.ref('core.decimal_amount')
        for line in self.line_ids:
            if line.currency_amount > 0:
                if line.in_bank_id.currency_id: # 如果填充了转入账户的币别，则说明转入账户为外币
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
        self.state = 'draft'
        return True


class money_transfer_order_line(models.Model):
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
