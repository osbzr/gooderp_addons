# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import except_orm


class money_order(models.Model):
    _inherit = 'money.order'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True)
    #  --test-enable -d gooderp_test -u money

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
        self.voucher_id.unlink()
        return res

    @api.multi
    def create_money_order_get_voucher(self, line_ids, partner, name):
        vouch_obj = self.env['voucher'].create({'date': self.date})
        self.write({'voucher_id': vouch_obj.id})
        for line in line_ids:
            if not line.bank_id.account_id:
                raise except_orm(u'错误', u'请配置%s的会计科目' % (line.bank_id.name))
            self.env['voucher.line'].create({
                'name': "%s收款单%s" % (partner.name, name), 'account_id': line.bank_id.account_id.id, 'debit': line.amount,
                'voucher_id': vouch_obj.id,
            })
            if partner.c_category_id:
                partner_account_id = partner.c_category_id.account_id.id
            else:
                partner_account_id = partner.s_category_id.account_id.id
            self.env['voucher.line'].create({
                'name': "%s收款单%s " % (partner.name, name), 'account_id': partner_account_id, 'credit': line.amount,
                'voucher_id': vouch_obj.id,
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
                'name': "%s收款单%s" % (partner.name, name), 'account_id': line.bank_id.account_id.id, 'credit': line.amount,
                'voucher_id': vouch_obj.id,
            })
            if partner.c_category_id:
                partner_account_id = partner.c_category_id.account_id.id
            else:
                partner_account_id = partner.s_category_id.account_id.id
            self.env['voucher.line'].create({
                'name': "%s 付款单 %s " % (partner.name, name), 'account_id': partner_account_id, 'debit': line.amount,
                'voucher_id': vouch_obj.id,
            })
        return vouch_obj


class money_invoice(models.Model):
    _inherit = 'money.invoice'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True)

    @api.multi
    def money_invoice_draft(self):
        res = super(money_invoice, self).money_invoice_draft()
        self.voucher_id.unlink()
        return res

    @api.multi
    def money_invoice_done(self):
        res = super(money_invoice, self).money_invoice_done()
        vals = {}
        vouch_obj = self.env['voucher'].create({'date': self.date})
        self.write({'voucher_id': vouch_obj.id})
        if not self.category_id.account_id:
            raise except_orm(u'错误', u'请配置%s的会计科目' % (self.category_id.name))

        if self.category_id.name == '销售':
            if not self.partner_id.c_category_id.account_id:
                raise except_orm(u'错误', u'请配置%s的会计科目' % (self.category_id.name))
            vals.update({'vouch_obj_id': vouch_obj.id, 'partner_name': self.partner_id.name, 'name': self.name, 'string': '源单',
                         'amount': self.amount, 'credit_account_id': self.category_id.account_id.id,
                         'debit_account_id': self.partner_id.c_category_id.account_id.id
                         })

        else:
            if not self.partner_id.s_category_id.account_id:
                raise except_orm(u'错误', u'请配置%s的会计科目' % (self.category_id.name))
            vals.update({'vouch_obj_id': vouch_obj.id, 'partner_name': self.partner_id.name, 'name': self.name, 'string': '源单',
                         'amount': abs(self.amount), 'credit_account_id': self.partner_id.s_category_id.account_id.id,
                         'debit_account_id': self.category_id.account_id.id
                         })
        self.create_voucher_line(vals)
        return res

    @api.multi
    def create_voucher_line(self, vals):
        self.env['voucher.line'].create({
            'name': "%s %s %s " % (vals.get('partner_name'), vals.get('string'), vals.get('name')), 'account_id': vals.get('debit_account_id'),
            'debit': vals.get('amount'), 'voucher_id': vals.get('vouch_obj_id'),
        })
        self.env['voucher.line'].create({
            'name': "%s %s %s" % (vals.get('partner_name'), vals.get('string'), vals.get('name')),
            'account_id': vals.get('credit_account_id'), 'credit': vals.get('amount'), 'voucher_id': vals.get('vouch_obj_id'),
        })
        return True


class other_money_order(models.Model):
    _inherit = 'other.money.order'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True)

    @api.multi
    def other_money_draft(self):
        res = super(other_money_order, self).other_money_draft()
        self.voucher_id.unlink()
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
                vals.update({'vouch_obj_id': vouch_obj.id, 'partner_name': self.partner_id.name, 'name': self.name, 'string': '其他收入单',
                             'amount': abs(line.amount), 'credit_account_id': line.category_id.account_id.id,
                             'debit_account_id': self.bank_id.account_id.id
                             })
                self.env['money.invoice'].create_voucher_line(vals)
        else:
            for line in self.line_ids:
                if not line.category_id.account_id:
                    raise except_orm(u'错误', u'请配置%s的会计科目' % (line.category_id.name))
                vals.update({'vouch_obj_id': vouch_obj.id, 'partner_name': self.partner_id.name, 'name': self.name, 'string': '其他支出单',
                             'amount': abs(line.amount), 'credit_account_id': self.bank_id.account_id.id,
                             'debit_account_id': line.category_id.account_id.id
                             })
                self.env['money.invoice'].create_voucher_line(vals)
        return res
