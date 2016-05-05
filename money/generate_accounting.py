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
from openerp import models, fields, api
from openerp.exceptions import except_orm


class money_order(models.Model):
    _inherit = 'money.order'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict')

    @api.multi
    def money_order_done(self):
        res = super(money_order, self).money_order_done()
        if self.type == 'get':
            self.create_money_order_get_voucher(self.line_ids, self.partner_id, self.name)
        else:
            self.create_money_order_pay_voucher(self.line_ids, self.partner_id, self.name)
        return res

    @api.multi
    def money_order_draft(self):
        res = super(money_order, self).money_order_draft()
        voucher, self.voucher_id = self.voucher_id, False
        voucher.unlink()
        return res

    @api.multi
    def create_money_order_get_voucher(self, line_ids, partner, name):
        vouch_obj = self.env['voucher'].create({'date': self.date})
        self.write({'voucher_id': vouch_obj.id})
        for line in line_ids:
            if not line.bank_id.account_id:
                raise except_orm(u'错误', u'请配置%s的会计科目' % (line.bank_id.name))
            self.env['voucher.line'].create({
                'name': u"%s收款单%s" % (partner.name, name), 'account_id': line.bank_id.account_id.id, 'debit': line.amount,
                'voucher_id': vouch_obj.id, 'partner_id': ''
            })
            if partner.c_category_id:
                partner_account_id = partner.c_category_id.account_id.id
            self.env['voucher.line'].create({
                'name': u"%s收款单%s " % (partner.name, name), 'account_id': partner_account_id, 'credit': line.amount,
                'voucher_id': vouch_obj.id, 'partner_id': partner.id
            })
        return vouch_obj

    @api.multi
    def create_money_order_pay_voucher(self, line_ids, partner, name):
        vouch_obj = self.env['voucher'].create({'date': self.date})
        self.write({'voucher_id': vouch_obj.id})
        for line in line_ids:
            if not line.bank_id.account_id:
                raise except_orm(u'错误', u'请配置%s的会计科目' % (line.bank_id.name))
            self.env['voucher.line'].create({
                'name': u"收款单%s" % (name), 'account_id': line.bank_id.account_id.id, 'credit': line.amount,
                'voucher_id': vouch_obj.id, 'partner_id': '',
            })
            if partner.s_category_id:
                partner_account_id = partner.s_category_id.account_id.id
            self.env['voucher.line'].create({
                'name': u"付款单 %s " % (name), 'account_id': partner_account_id, 'debit': line.amount,
                'voucher_id': vouch_obj.id, 'partner_id': partner.id
            })
        return vouch_obj


class money_invoice(models.Model):
    _inherit = 'money.invoice'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict')

    @api.multi
    def money_invoice_draft(self):
        res = super(money_invoice, self).money_invoice_draft()
        voucher, self.voucher_id = self.voucher_id, False
        voucher.unlink()
        return res

    @api.multi
    def money_invoice_done(self):
        res = super(money_invoice, self).money_invoice_done()
        vals = {}
        vouch_obj = self.env['voucher'].create({'date': self.date})
        self.write({'voucher_id': vouch_obj.id})
        if not self.category_id.account_id:
            raise except_orm(u'错误', u'请配置%s的会计科目' % (self.category_id.name))
        if self.partner_id.c_category_id:
            partner_account_id = self.partner_id.c_category_id.account_id.id
        else:
            partner_account_id = self.partner_id.s_category_id.account_id.id

        if not partner_account_id:
            raise except_orm(u'错误', u'请配置%s的会计科目' % (self.category_id.name))
        if self.category_id.type == 'income':
            vals.update({'vouch_obj_id': vouch_obj.id, 'partner_credit': self.partner_id.id, 'name': self.name, 'string': u'源单',
                         'amount': self.amount, 'credit_account_id': self.category_id.account_id.id, 'partner_debit': '',
                         'debit_account_id': partner_account_id
                         })

        else:
            vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'string': u'源单',
                         'amount': abs(self.amount), 'credit_account_id': partner_account_id,
                         'debit_account_id': self.category_id.account_id.id, 'partner_credit': "", 'partner_debit': self.partner_id.id
                         })
        self.create_voucher_line(vals)
        return res

    @api.multi
    def create_voucher_line(self, vals):
        self.env['voucher.line'].create({
            'name': u"%s %s " % (vals.get('string'), vals.get('name')), 'account_id': vals.get('debit_account_id'),
            'debit': vals.get('amount'), 'voucher_id': vals.get('vouch_obj_id'), 'partner_id': vals.get('partner_debit', ''),
        })
        self.env['voucher.line'].create({
            'name': u"%s %s" % (vals.get('string'), vals.get('name')), 'partner_id': vals.get('partner_credit', ''),
            'account_id': vals.get('credit_account_id'), 'credit': vals.get('amount'), 'voucher_id': vals.get('vouch_obj_id'),
        })
        return True


class other_money_order(models.Model):
    _inherit = 'other.money.order'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict')

    @api.multi
    def other_money_draft(self):
        res = super(other_money_order, self).other_money_draft()
        voucher, self.voucher_id = self.voucher_id, False
        voucher.unlink()
        return res

    @api.multi
    def other_money_done(self):
        res = super(other_money_order, self).other_money_done()
        vals = {}
        vouch_obj = self.env['voucher'].create({'date': self.date})
        self.write({'voucher_id': vouch_obj.id})
        if not self.bank_id.account_id:
            raise except_orm(u'错误', u'请配置%s的会计科目' % (self.bank_id.name))
        if self.type == 'other_get':
            for line in self.line_ids:
                if not line.category_id.account_id:
                    raise except_orm(u'错误', u'请配置%s的会计科目' % (line.category_id.name))
                vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'string': u'其他收入单',

                             'amount': abs(line.amount), 'credit_account_id': line.category_id.account_id.id,
                             'debit_account_id': self.bank_id.account_id.id, 'partner_credit': self.partner_id.id, 'partner_debit': ''
                             })
                self.env['money.invoice'].create_voucher_line(vals)
        else:
            for line in self.line_ids:
                if not line.category_id.account_id:
                    raise except_orm(u'错误', u'请配置%s的会计科目' % (line.category_id.name))
                vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'string': u'其他支出单',

                             'amount': abs(line.amount), 'credit_account_id': self.bank_id.account_id.id,
                             'debit_account_id': line.category_id.account_id.id, 'partner_credit': '', 'partner_debit': self.partner_id.id
                             })
                self.env['money.invoice'].create_voucher_line(vals)
        return res


class money_transfer_order(models.Model):
    _inherit = 'money.transfer.order'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict')

    @api.multi
    def money_transfer_done(self):
        res = super(money_transfer_order, self).money_transfer_done()
        vouch_obj = self.env['voucher'].create({'date': self.date})
        vals = {}
        self.write({'voucher_id': vouch_obj.id})
        for line in self.line_ids:
            vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'string': u'资金转账单',
                         'amount': abs(line.amount), 'credit_account_id': line.out_bank_id.account_id.id,
                         'debit_account_id': line.in_bank_id.account_id.id,
                         })
            self.env['money.invoice'].create_voucher_line(vals)
        return res

    @api.multi
    def money_transfer_draft(self):
        res = super(money_transfer_order, self).money_transfer_draft()
        voucher, self.voucher_id = self.voucher_id, False
        voucher.unlink()
        return res
