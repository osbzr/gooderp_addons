# -*- coding: utf-8 -*-
# ##############################################################################
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
from odoo import models, fields, api
from odoo.exceptions import UserError


class MoneyInvoice(models.Model):
    _inherit = 'money.invoice'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict',
                                 copy=False,
                                 help=u'结算单确认时生成的对应凭证')

    @api.multi
    def money_invoice_draft(self):
        """
        撤销确认结算单时，撤销确认凭证
        :return: 
        """
        res = super(MoneyInvoice, self).money_invoice_draft()
        for invoice in self:
            voucher, invoice.voucher_id = invoice.voucher_id, False
            if voucher.state == 'done':
                voucher.voucher_draft()
            # 始初化单反审核只删除明细行：生成初始化凭证时，不生成往来单位对方的科目，所以要删除相关明细行
            if invoice.is_init:
                vouch_obj = self.env['voucher'].search(
                    [('id', '=', voucher.id)])
                vouch_obj_lines = self.env['voucher.line'].search([
                    ('voucher_id', '=', vouch_obj.id),
                    ('partner_id', '=', invoice.partner_id.id),
                    ('init_obj', '=', 'money_invoice'), ])
                for vouch_obj_line in vouch_obj_lines:
                    vouch_obj_line.unlink()
            else:   # 非初始化单反审核时删除凭证
                voucher.unlink()
        return res

    @api.multi
    def money_invoice_done(self):
        """
        确认结算单时，创建凭证并确认
        :return: 
        """
        res = super(MoneyInvoice, self).money_invoice_done()
        vals = {}
        # 初始化单的话，先找是否有初始化凭证，没有则新建一个
        for invoice in self:
            if invoice.is_init:
                vouch_obj = self.env['voucher'].search(
                    [('is_init', '=', True)])
                if not vouch_obj:
                    vouch_obj = self.env['voucher'].create(
                        {'date': invoice.date,
                         'is_init': True,
                         'ref': '%s,%s' % (self._name, self.id)})
                invoice.write({'voucher_id': vouch_obj.id})
            else:
                vouch_obj = self.env['voucher'].create({'date': invoice.date, 'ref': '%s,%s' % (self._name, self.id)})
                invoice.write({'voucher_id': vouch_obj.id})
            if not invoice.category_id.account_id:
                raise UserError(u'请配置%s的会计科目' % (invoice.category_id.name))
            partner_cat = invoice.category_id.type == 'income' and invoice.partner_id.c_category_id or invoice.partner_id.s_category_id
            partner_account_id = partner_cat.account_id.id
            if not partner_account_id:
                raise UserError(u'请配置%s的会计科目' % (partner_cat.name))
            if invoice.category_id.type == 'income':
                vals.update({'vouch_obj_id': vouch_obj.id, 'partner_credit': invoice.partner_id.id, 'name': invoice.name, 'string': invoice.note or '',
                             'amount': invoice.amount, 'credit_account_id': invoice.category_id.account_id.id, 'partner_debit': invoice.partner_id.id,
                             'debit_account_id': partner_account_id, 'sell_tax_amount': invoice.tax_amount or 0,
                             'credit_auxiliary_id': invoice.auxiliary_id.id, 'currency_id': invoice.currency_id.id or '',
                             'rate_silent': self.env['res.currency'].get_rate_silent(self.date, invoice.currency_id.id) or 0,
                             })
            else:
                vals.update({'vouch_obj_id': vouch_obj.id, 'name': invoice.name, 'string': invoice.note or '',
                             'amount': invoice.amount, 'credit_account_id': partner_account_id,
                             'debit_account_id': invoice.category_id.account_id.id, 'partner_debit': invoice.partner_id.id,
                             'partner_credit': invoice.partner_id.id, 'buy_tax_amount': invoice.tax_amount or 0,
                             'debit_auxiliary_id': invoice.auxiliary_id.id, 'currency_id': invoice.currency_id.id or '',
                             'rate_silent': self.env['res.currency'].get_rate_silent(self.date, invoice.currency_id.id) or 0,
                             })
            if invoice.is_init:
                vals.update({'init_obj': 'money_invoice', })
            invoice.create_voucher_line(vals)
            # 删除初始非需要的凭证明细行,不确认凭证
            if invoice.is_init:
                vouch_line_ids = self.env['voucher.line'].search([
                    ('account_id', '=', invoice.category_id.account_id.id),
                    ('init_obj', '=', 'money_invoice')])
                for vouch_line_id in vouch_line_ids:
                    vouch_line_id.unlink()
            else:
                vouch_obj.voucher_done()
        return res

    @api.multi
    def create_voucher_line(self, vals):
        if vals.get('currency_id') == self.env.user.company_id.currency_id.id or not vals.get('rate_silent'):
            debit = credit = vals.get('amount')
            sell_tax_amount = vals.get('sell_tax_amount')
        else:
            # 外币免税
            debit = credit = vals.get('amount') * vals.get('rate_silent')
        # 把税从金额中减去
        if vals.get('buy_tax_amount'):  # 如果传入了进项税
            debit = vals.get('amount') - vals.get('buy_tax_amount')
        if vals.get('sell_tax_amount'):  # 如果传入了销项税
            credit = vals.get('amount') - sell_tax_amount
        # 借方行
        currency_id = vals.get(
            'currency_id') or self.env.user.company_id.currency_id.id
        if currency_id != self.env.user.company_id.currency_id.id:  # 结算单上是外币
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'account_id': vals.get('debit_account_id'),
                'debit': debit,
                'voucher_id': vals.get('vouch_obj_id'),
                'partner_id': vals.get('partner_debit', ''),
                'auxiliary_id': vals.get('debit_auxiliary_id', False),
                'currency_id': vals.get('currency_id'),
                'currency_amount': vals.get('amount'),
                'rate_silent': vals.get('rate_silent'),
                'init_obj': vals.get('init_obj', False),
            })
        else:   # 结算单上是本位币
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'account_id': vals.get('debit_account_id'),
                'debit': debit,
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
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'account_id': self.env.user.company_id.import_tax_account.id, 'debit': vals.get('buy_tax_amount'), 'voucher_id': vals.get('vouch_obj_id'),
            })
        # 贷方行
        currency_id = vals.get(
            'currency_id') or self.env.user.company_id.currency_id.id
        if currency_id != self.env.user.company_id.currency_id.id:
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'partner_id': vals.get('partner_credit', ''),
                'account_id': vals.get('credit_account_id'),
                'credit': credit,
                'voucher_id': vals.get('vouch_obj_id'),
                'auxiliary_id': vals.get('credit_auxiliary_id', False),
                'currency_amount': vals.get('amount'),
                'rate_silent': vals.get('rate_silent'), 'currency_id': vals.get('currency_id'),
                'init_obj': vals.get('init_obj', False),
            })
        else:
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'partner_id': vals.get('partner_credit', ''),
                'account_id': vals.get('credit_account_id'),
                'credit': credit,
                'voucher_id': vals.get('vouch_obj_id'),
                'auxiliary_id': vals.get('credit_auxiliary_id', False),
                'init_obj': vals.get('init_obj', False),
            })
        # 销项税行
        if vals.get('sell_tax_amount'):
            if not self.env.user.company_id.output_tax_account:
                raise UserError(
                    u'您还没有配置公司的销项税科目。\n请通过"配置-->高级配置-->公司"菜单来设置销项税科目!')
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'account_id': self.env.user.company_id.output_tax_account.id, 'credit': sell_tax_amount, 'voucher_id': vals.get('vouch_obj_id'),
            })

        return True
