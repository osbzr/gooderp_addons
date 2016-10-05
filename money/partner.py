# -*- coding: utf-8 -*-

from odoo import fields, models, api
import odoo.addons.decimal_precision as dp


class partner(models.Model):
    _inherit = 'partner'
    _description = u'查看业务伙伴对账单'

    @api.multi
    def _set_receivable_init(self):
        if self.receivable_init:
            # 如果有前期初值，删掉已前的单据
            money_invoice_id = self.env['money.invoice'].search([
                '&',
                ('partner_id', '=', self.id),
                ('is_init', '=', True)])
            if money_invoice_id:
                money_invoice_id.money_invoice_draft()
                money_invoice_id.unlink()
            # 创建源单
            categ = self.env.ref('money.core_category_sale')
            source_id = self.env['money.invoice'].create({
            'name': "期初应收余额",
            'partner_id': self.id,
            'category_id': categ.id,
            'is_init': True,
            'date': self.env.user.company_id.start_date,
            'amount': self.receivable_init,
            'reconciled': 0,
            'to_reconcile': self.receivable_init,
            'date_due': self.env.user.company_id.start_date,
            'state': 'draft',
             })

    @api.multi
    def _set_payable_init(self):
        if self.payable_init:
            # 如果有前期初值，删掉已前的单据
            money_invoice_id = self.env['money.invoice'].search([
                '&',
                ('partner_id', '=', self.id),
                ('is_init', '=', True)])
            if money_invoice_id:
                money_invoice_id.money_invoice_draft()
                money_invoice_id.unlink()
            # 创建源单
            categ = self.env.ref('money.core_category_purchase')
            source_id = self.env['money.invoice'].create({
            'name': "期初应付余额",
            'partner_id': self.id,
            'category_id': categ.id,
            'is_init': True,
            'date': self.env.user.company_id.start_date,
            'amount': self.payable_init,
            'reconciled': 0,
            'to_reconcile': self.payable_init,
            'date_due': self.env.user.company_id.start_date,
            'state': 'draft',
             })

    receivable_init = fields.Float(u'应收期初', 
                                   digits=dp.get_precision('Amount'),
                                   inverse=_set_receivable_init,
                                   help=u'客户的应收期初余额')
    payable_init = fields.Float(u'应付期初', 
                           digits=dp.get_precision('Amount'),
                           inverse=_set_payable_init,
                        help=u'供应商的应付期初余额')

    @api.multi
    def partner_statements(self):
        self.ensure_one()
        view = self.env.ref('money.partner_statements_report_wizard_form')
        ctx = {'default_partner_id': self.id}
        if self.c_category_id.type == 'customer':
            ctx.update({'default_customer': True})
        else:
            ctx.update({'default_supplier': True})

        return {
            'name': u'业务伙伴对账单向导',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view.id, 'form')],
            'res_model': 'partner.statements.report.wizard',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'target': 'new',
        }


class bank_account(models.Model):
    _inherit = 'bank.account'
    _description = u'查看账户对账单'

    @api.multi
    def _set_init_balance(self):
        if self.init_balance:
            # 如果有前期初值，删掉已前的单据
            other_money_id = self.env['other.money.order'].search([
                '&',
                ('bank_id', '=', self.id),
                ('is_init', '=', True)])
            if other_money_id:
                other_money_id.other_money_draft()
                other_money_id.unlink()
            # 资金期初 生成 其他收入
            other_money_init = self.env['other.money.order'].create({
                'name': "期初",
                'type': 'other_get',
                'bank_id': self.id,
                'date': self.env.user.company_id.start_date,
                'is_init': True,
                'line_ids': [(0, 0, {
                    'category_id': self.env.ref('money.core_category_init').id,
                    'amount': self.init_balance,
                    'tax_rate': 0,
                })],
                'state': 'draft'
            })
            # 审核 其他收入单
            other_money_init.other_money_done()

    init_balance = fields.Float(u'期初',
                               digits=dp.get_precision('Amount'),
                               inverse=_set_init_balance,
                               help=u'资金的期初余额')

    @api.multi
    def bank_statements(self):
        self.ensure_one()
        view = self.env.ref('money.bank_statements_report_wizard_form')

        return {
            'name': u'账户对账单向导',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view.id, 'form')],
            'res_model': 'bank.statements.report.wizard',
            'type': 'ir.actions.act_window',
            'context': {'default_bank_id': self.id},
            'target': 'new',
        }
