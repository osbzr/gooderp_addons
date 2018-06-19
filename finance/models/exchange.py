# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class Currency(models.Model):
    _inherit = 'res.currency'

    @api.multi
    def get_rate_silent(self, date, currency_id):
        currency = self.env['res.currency'].search([('id', '=', currency_id)])
        rate = currency.rate
        return rate


class CreateExchangeWizard(models.TransientModel):
    """生成每月汇况损益的向导 根据输入的期间"""
    _name = "create.exchange.wizard"
    _description = u'期末调汇向导'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    @api.model
    def _get_last_date(self):
        return self.env['finance.period'].get_period_month_date_range(self.env['finance.period'].get_date_now_period_id())[1]

    date = fields.Date(u'记帐日期', required=True, default=_get_last_date)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    # todo 增加一个可以看到最后汇率的界面
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def create_partner_exchange_line(self, vals):
        '''
        有partner的汇兑损益
        '''
        account_id = vals.get('account_id')
        voucher_lines = self.env['voucher.line'].search(
            [('account_id', '=', account_id),
             ('state', '=', 'done')])
        account = vals.get('account')
        res = {}
        for line in voucher_lines:
            if line.partner_id.id not in res:
                res[line.partner_id.id] = {'currency': 0,
                                           'total_debit': 0,
                                           'total_credit': 0}
            val = res[line.partner_id.id]
            if line.debit == 0:
                val.update({'currency': val.get('currency') + line.currency_amount,
                            'total_debit': val.get('total_debit') + line.debit,
                            'total_credit': val.get('total_credit') + line.credit})
            else:
                val.update({'currency': val.get('currency') - line.currency_amount,
                            'total_debit': val.get('total_debit') + line.debit,
                            'total_credit': val.get('total_credit') + line.credit})
            exp = val.get('currency') * vals.get('rate_silent') + \
                val.get('total_debit') - val.get('total_credit')

            if account.balance_directions == 'in':
                '''科目为借，则生成借方凭证行,差额为0的凭证行不生成'''
                if exp != 0:
                    val.update({'name': u"汇兑损益",
                                'account_id': vals.get('account_id'),
                                'debit': -exp,
                                'credit': 0,
                                'voucher_id': vals.get('vouch_obj_id'),
                                'currency_id': False,
                                'currency_amount': False,
                                'rate_silent': False,
                                'partner_id': line.partner_id.id,
                                })

            if account.balance_directions == 'out':
                '''科目为贷，则生成贷方凭证行,差额为0的凭证行不生成'''
                if exp != 0:
                    val.update({'name': u"汇兑损益",
                                'account_id': vals.get('account_id'),
                                'credit': exp,
                                'voucher_id': vals.get('vouch_obj_id'),
                                'currency_id': False,
                                'currency_amount': False,
                                'rate_silent': False,
                                'partner_id': line.partner_id.id,
                                })

        '''如果所有差额都为0，则无会计科目，则不生成明细行'''
        for partner_id, val in res.iteritems():
            del val['currency'], val['total_debit'], val['total_credit']
            if val:
                self.env['voucher.line'].create(
                    dict(val, partner_id=partner_id))

    @api.multi
    def create_account_exchange_line(self, vals):
        '''
        无partner的汇兑损益
        '''
        account_id = vals.get('account_id')
        voucher_lines = self.env['voucher.line'].search(
            [('account_id', '=', account_id),
             ('state', '=', 'done')])
        account = vals.get('account')
        currency_amount = 0
        debit = 0
        credit = 0
        for line in voucher_lines:
            if line.debit:
                currency_amount = currency_amount + line.currency_amount
            else:
                currency_amount = currency_amount - line.currency_amount
            debit = line.debit + debit
            credit = line.credit + credit
        if account.balance_directions == 'in':
            '''科目为借，则生成借方凭证行,差额为0的凭证行不生成'''
            if currency_amount * vals.get('rate_silent') - debit + credit != 0:
                self.env['voucher.line'].create({
                    'name': u"汇兑损益",
                    'account_id': account_id,
                    'debit': currency_amount * vals.get('rate_silent') - debit + credit,
                    'voucher_id': vals.get('vouch_obj_id'),
                    'currency_id': False,
                    'currency_amount': False,
                    'rate_silent': False,
                })
        else:
            '''科目为贷，则生成贷方凭证行,差额为0的凭证行不生成'''
            if currency_amount * vals.get('rate_silent') - credit + debit != 0:
                self.env['voucher.line'].create({
                    'name': u"汇兑损益",
                    'account_id': account_id,
                    'credit': currency_amount * vals.get('rate_silent') - credit + debit,
                    'voucher_id': vals.get('vouch_obj_id'),
                    'currency_id': False,
                    'currency_amount': False,
                    'rate_silent': False,
                })

    @api.multi
    def create_exchang_line(self, vals):
        '''
        当有主营业务收入,结汇等不需要汇兑损益的科目出现后，汇兑损益将不平，就会出现财务费用汇兑损益，
        '''
        vouch_obj = vals.get('vouch_obj_id')
        voucher = self.env['voucher'].search([('id', '=', vouch_obj)])
        voucher_lines = voucher.line_ids
        account_id = self.env.ref('finance.account_exchange')
        exp = 0

        for line in voucher_lines:
            exp = line.credit - line.debit + exp
        if exp != 0:
            self.env['voucher.line'].create({
                'name': u"汇兑损益",
                'account_id': account_id.account_id.id,
                'credit': -exp,
                'voucher_id': vals.get('vouch_obj_id'),
                'currency_id': False,
                'currency_amount': False,
                'rate_silent': False,
            })

    def create_exchange(self):
        vouch_obj = self.env['voucher'].create({'date': self.date})
        '''只有外币＋期末需要调汇的科目才会能生成调汇凭证的明细行'''
        vals = {}
        for account_id in self.env['finance.account'].search([
            ('currency_id', '!=', self.env.user.company_id.currency_id.id),
            ('currency_id', '!=', False),
                ('exchange', '=', True)]):
            rate_silent = self.env['res.currency'].get_rate_silent(
                self.date, account_id.currency_id.id) or 0
            vals.update({'account_id': account_id.id,
                         'account': account_id,
                         'vouch_obj_id': vouch_obj.id,
                         'rate_silent': rate_silent,
                         })
            if account_id.auxiliary_financing:
                self.create_partner_exchange_line(vals)
            else:
                self.create_account_exchange_line(vals)
        '''
        当出现结汇，主营业务收入等一方不为需期末调汇科目时会出现一方需要调汇，一方不需要调汇，那时期末前面的明细行就会不平衡，就需要贷财务费用－汇兑损益
        '''
        self.create_exchang_line(vals)

        if not vouch_obj.line_ids:
            vouch_obj.unlink()


class RatePeriod(models.Model):
    """记录本月结算汇兑损益时的汇率，用于反结算后，汇兑损益正确时汇率正确"""
    _name = "rate.period"
    _description = u'记录本月结算汇兑损益时的汇率'

    name = fields.Many2one('res.currency', u'币别', required=True)
    account_accumulated_depreciation = fields.Many2one(
        'finance.account', u'累计折旧科目', required=True)
    account_asset = fields.Many2one(
        'finance.account', u'固定资产科目', required=True)
    account_depreciation = fields.Many2one(
        'finance.account', u'折旧费用科目', required=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
