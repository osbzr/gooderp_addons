# -*- coding: utf-8 -*-

from odoo import fields, models, api
import odoo.addons.decimal_precision as dp
from odoo.tools import float_is_zero
from odoo.exceptions import UserError, ValidationError


class Partner(models.Model):
    '''查看业务伙伴对账单'''
    _inherit = 'partner'

    def _init_source_create(self, name, partner_id, category_id, is_init, date,
                            amount, reconciled, to_reconcile, date_due, state):
        if not float_is_zero(amount, 2):
            return self.env['money.invoice'].create({
                'name': name,
                'partner_id': partner_id,
                'category_id': category_id,
                'is_init': is_init,
                'date': date,
                'amount': amount,
                'reconciled': reconciled,
                'to_reconcile': to_reconcile,
                'date_due': date_due,
                'state': state,
            })

    @api.one
    def _set_receivable_init(self):
        # 如果有前期初值，删掉已前的单据
        money_invoice_id = self.env['money.invoice'].search([
            ('partner_id', '=', self.id),
            ('is_init', '=', True)])
        if money_invoice_id:
            money_invoice_id.money_invoice_draft()
            money_invoice_id.unlink()
        if self.receivable_init:
            # 创建结算单
            categ = self.env.ref('money.core_category_sale')
            self._init_source_create("期初应收余额", self.id, categ.id, True,
                                     self.env.user.company_id.start_date, self.receivable_init, 0,
                                     self.receivable_init, self.env.user.company_id.start_date, 'draft')

    @api.one
    def _set_payable_init(self):
        # 如果有前期初值，删掉已前的单据
        money_invoice_id = self.env['money.invoice'].search([
            ('partner_id', '=', self.id),
            ('is_init', '=', True)])
        if money_invoice_id:
            money_invoice_id.money_invoice_draft()
            money_invoice_id.unlink()
        if self.payable_init:
            # 创建结算单
            categ = self.env.ref('money.core_category_purchase')
            self._init_source_create("期初应付余额", self.id, categ.id, True,
                                     self.env.user.company_id.start_date, self.payable_init, 0,
                                     self.payable_init, self.env.user.company_id.start_date, 'draft')

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
        """
        调用这个方法弹出 业务伙伴对账单向导
        :return:
        """
        self.ensure_one()
        ctx = {'default_partner_id': self.id}
        # 既是客户又是供应商的业务伙伴，根据是在客户还是供应商界面点击的 查看对账单 按钮，显示不同的明细
        if self.c_category_id.type == 'customer' and self.env.context.get('is_customer_view'):
            view = self.env.ref('money.customer_statements_report_wizard_form')
            ctx.update({'default_customer': True})
        else:
            view = self.env.ref('money.partner_statements_report_wizard_form')
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

    @api.one
    @api.constrains('receivable_init', 'payable_init')
    def _check_receivable_init(self):
        '''应收期初和应付期初只能有一个存在'''
        if self.receivable_init and self.payable_init:
            raise UserError(u'应收期初和应付期初不能同时存在')


class BankAccount(models.Model):
    '''查看账户对账单'''
    _inherit = 'bank.account'

    @api.one
    def _set_init_balance(self):
        """
        如果  init_balance 字段里面有值则 进行 一系列的操作。
        :return:
        """
        start_date = self.env.user.company_id.start_date
        start_date_period_id = self.env['finance.period'].search_period(start_date)
        if self.init_balance and start_date_period_id.is_closed:
            raise UserError(u'初始化期间(%s)已结账！' % start_date_period_id.name)
        # 如果有前期初值，删掉已前的单据
        other_money_id = self.env['other.money.order'].search([
            ('bank_id', '=', self.id),
            ('is_init', '=', True)])
        if other_money_id:
            other_money_id.other_money_draft()
            other_money_id.unlink()
        if self.init_balance:
            # 资金期初 生成 其他收入
            other_money_init = self.with_context(type='other_get').env['other.money.order'].create({
                'bank_id': self.id,
                'date': self.env.user.company_id.start_date,
                'is_init': True,
                'line_ids': [(0, 0, {
                    'category_id': self.env.ref('money.core_category_init').id,
                    'amount': self.init_balance,
                    'tax_rate': 0,
                    'tax_amount': 0,
                })],
                'state': 'draft',
                'currency_amount': self.currency_amount,
            })
            # 审核 其他收入单
            other_money_init.other_money_done()


    init_balance = fields.Float(u'期初',
                                digits=dp.get_precision('Amount'),
                                inverse=_set_init_balance,
                                help=u'资金的期初余额')

    @api.multi
    def bank_statements(self):
        """
        账户对账单向导 调用这个方法弹出 账户对账单向导
        :return:
        """
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
