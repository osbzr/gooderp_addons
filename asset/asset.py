# -*- coding: utf-8 -*-

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError
from datetime import datetime

# 字段只读状态
READONLY_STATES = {
        'done': [('readonly', True)],
    }

class asset_category(models.Model):
    '''固定资产分类'''
    _name = 'asset.category'
    name = fields.Char(u'名称', required=True)
    account_depreciation2 = fields.Many2one(
        'finance.account', u'累计折旧科目', required=True)
    account_asset = fields.Many2one(
        'finance.account', u'固定资产科目', required=True)
    account_depreciation = fields.Many2one(
        'finance.account', u'折旧费用科目', required=True)
    depreciation_number = fields.Float(u'折旧期间数', required=True)
    depreciation_value = fields.Float(u'最终残值率%', required=True)
    clean_income = fields.Many2one(
        'finance.account', u'固定资产清理收入科目', required=True)
    clean_costs = fields.Many2one(
        'finance.account', u'固定资产清理成本科目', required=True)


class asset(models.Model):
    '''固定资产'''
    _name = 'asset'
    _order = "code"

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    @api.one
    @api.depends('cost','tax')
    def _get_amount(self):
        self.amount = self.cost + self.tax

    @api.one
    @api.depends('cost','depreciation_value2')
    def _get_surplus_value(self):
        self.surplus_value = self.cost - self.depreciation_value2
        self.depreciation_value = self.attribute.depreciation_value * self.cost / 100

    @api.one
    @api.depends('surplus_value','depreciation_value','depreciation_number')
    def _get_cost_depreciation(self):
        self.cost_depreciation = (self.surplus_value - self.depreciation_value) / (self.depreciation_number or 1)

    code = fields.Char(u'编码', required="1", states=READONLY_STATES)
    date = fields.Date(u'记帐日期', required=True, states=READONLY_STATES)
    name = fields.Char(u'名称', required=True, states=READONLY_STATES)
    att_count = fields.Integer(u'附单据', default=1, states=READONLY_STATES)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已审核'),
                              ('clean', u'已清理')], u'状态', default='draft')
    cost = fields.Float(u'金额', digits=dp.get_precision(u'金额'), required=True, states=READONLY_STATES)
    tax = fields.Float(u'税额', digits=dp.get_precision(u'税额'), required=True, states=READONLY_STATES)
    amount = fields.Float(u'价税合计', digits=dp.get_precision(u'金额'), store=True, compute='_get_amount')
    bank_account = fields.Many2one('bank.account', u'结算账户', ondelete='restrict', states=READONLY_STATES)
    partner_id = fields.Many2one('partner', u'往来单位', ondelete='restrict', states=READONLY_STATES)
    other_system = fields.Boolean(u'初始化固定资产', states=READONLY_STATES)
    no_depreciation = fields.Boolean(u'不折旧')
    attribute = fields.Many2one('asset.category', u'固定资产分类', ondelete='restrict', required=True, states=READONLY_STATES)
    depreciation_value2 = fields.Float(u'以前折旧', digits=dp.get_precision(u'金额'), required=True, states=READONLY_STATES)
    depreciation_number = fields.Float(u'折旧期间数', required=True, states=READONLY_STATES)
    surplus_value = fields.Float(u'残值', digits=dp.get_precision(u'金额'), store=True, compute='_get_surplus_value')
    depreciation_value = fields.Float(u'最终残值', digits=dp.get_precision(u'金额'), required=True, states=READONLY_STATES)
    account_credit = fields.Many2one(
        'finance.account', u'固定资产贷方科目', required=True, states=READONLY_STATES)
    account_depreciation = fields.Many2one(
        'finance.account', u'折旧费用科目', required=True, states=READONLY_STATES)
    account_depreciation2 = fields.Many2one(
        'finance.account', u'累计折旧科目', required=True, states=READONLY_STATES)
    account_asset = fields.Many2one(
        'finance.account', u'固定资产科目', required=True, states=READONLY_STATES)
    cost_depreciation = fields.Float(u'每月折旧额', digits=dp.get_precision(u'金额'), store=True, compute='_get_cost_depreciation')
    line_ids = fields.One2many('asset.line', 'order_id', u'折旧明细行',
                               states=READONLY_STATES, copy=True)
    chang_ids = fields.One2many('chang.line', 'order_id', u'变更明细行',
                               states=READONLY_STATES, copy=True)
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict')
    money_invoice = fields.Many2one('money.invoice', u'对应源单', readonly=True, ondelete='restrict')
    other_money_order = fields.Many2one('other.money.order', u'对应其他应付款单', readonly=True, ondelete='restrict')
    @api.one
    @api.onchange('attribute')
    def onchange_attribute(self):
        '''当固定资产分类发生变化时，折旧期间数，固定资产科目，累计折旧科目，最终残值同时变化'''
        if self.attribute:
            self.depreciation_number = self.attribute.depreciation_number
            self.account_asset = self.attribute.account_asset
            self.account_depreciation2 = self.attribute.account_depreciation2
            self.account_depreciation = self.attribute.account_depreciation
            self.depreciation_value = self.attribute.depreciation_value * self.cost / 100

    @api.one
    @api.onchange('cost')
    def onchange_cost(self):
        '''当固定资产金额发生变化时，最终残值，价格合计,残值，每月折旧额变化'''
        if self.cost:
            self.depreciation_value = self.attribute.depreciation_value * self.cost / 100

    @api.one
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''当合作伙伴发生变化时，固定资产贷方科目变化'''
        if self.partner_id:
            self.account_credit = self.partner_id.s_category_id.account_id

    @api.one
    @api.onchange('bank_account')
    def onchange_bank_account(self):
        '''当结算帐户发生变化时，固定资产贷方科目变化'''
        if self.bank_account:
            self.account_credit = self.bank_account.account_id

    @api.one
    def asset_done(self):
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        if self.period_id.is_closed is True:
            raise except_orm(u'错误', u'该会计期间已结账！不能审核')
        if self.cost <= 0 :
            raise except_orm(u'错误', u'金额必须大于0！')
        if self.tax < 0 :
            raise except_orm(u'错误', u'税额必须大于0！')
        if self.depreciation_value2 < 0 :
            raise except_orm(u'错误', u'以前折旧必须大于0！')
        '''非初始化固定资产生成凭证'''
        if not self.other_system :
            vals = {}
            if self.partner_id and self.partner_id.s_category_id.account_id.id == self.account_credit.id :
                categ = self.env.ref('money.core_category_purchase')
                money_invoice = self.env['money.invoice'].create({
                        'name': u'固定资产'+self.code,
                        'partner_id': self.partner_id.id,
                        'category_id': categ.id,
                        'date': self.date,
                        'amount': self.amount,
                        'reconciled': 0,
                        'to_reconcile': self.amount,
                        'date_due': fields.Date.context_today(self),
                        'state': 'draft',
                        'tax_amount': self.tax
                })
                self.write({'money_invoice': money_invoice.id})
                print self.cost,money_invoice.voucher_id.id
                '''变化科目'''
                chang_account = self.env['voucher.line'].search(['&',('voucher_id', '=', money_invoice.voucher_id.id),('debit', '=', self.cost)])
                chang_account.write({'account_id': self.account_asset.id})

            elif self.bank_account and self.account_credit.id == self.bank_account.account_id.id :
                category_id = self.env.ref('asset.asset').id
                other_money_order = self.env['other.money.order'].create({
                    'state': 'draft',
                    'partner_id': self.partner_id,
                    'date': self.date,
                    'bank_id': self.bank_account.id,
                    'type': 'other_pay',
                    'context' : 'other_pay'
                })
                self.write({'other_money_order': other_money_order.id})
                self.env['other.money.order.line'].create({
                    'other_money_id': other_money_order.id ,
                    'amount': self.cost ,
                    'tax_rate': self.tax/self.cost*100 ,
                    'tax_amount' : self.tax,
                    'category_id': category_id
                })
            else :
                vouch_obj = self.env['voucher'].create({'date': self.date})
                self.write({'voucher_id': vouch_obj.id})
                vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'string': u'固定资产',
                     'amount': self.amount, 'credit_account_id': self.account_credit.id,
                     'debit_account_id': self.account_asset.id, 'partner_credit': self.partner_id.id, 'partner_debit': '',
                     'buy_tax_amount': self.tax or 0
                     })
                self.env['money.invoice'].create_voucher_line(vals)

        self.state = 'done'

    @api.one
    def asset_draft(self):
        if self.state == 'draft':
            raise except_orm(u'错误', u'请不要重复反审核！')
        if self.period_id.is_closed is True:
            raise except_orm(u'错误', u'该会计期间已结账！不能反审核')
        '''生成凭证'''


class CreateCleanWizard(models.TransientModel):
    '''固定资产清理'''
    _name = 'create.clean.wizard'
    _description = 'Create Clean Wizard form'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    date = fields.Date(u'清理日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    clean_cost = fields.Float(u'清理费用', required=True)
    residual_income = fields.Float(u'残值收入', required=True)
    sell_tax_amount = fields.Float(u'销项税额', required=True)
    bank_account = fields.Many2one('bank.account', u'结算账户')

    @api.one
    def create_clean_account(self):
        asset = self.env['asset'].browse(self.env.context.get('active_id'))
        asset.no_depreciation = 1
        asset.state = 'clean'
        '''按发票收入生成收入单'''
        get_category_id = self.env.ref('asset.asset_clean_get').id
        other_money_order = self.env['other.money.order'].create({
                    'state': 'draft',
                    'partner_id': None,
                    'date': self.date,
                    'bank_id': self.bank_account.id,
                    'type': 'other_get',
                    'context' : 'other_get'
                })
        self.env['other.money.order.line'].create({
                    'other_money_id': other_money_order.id,
                    'amount': self.residual_income,
                    'tax_rate': self.sell_tax_amount / self.residual_income * 100,
                    'tax_amount' : self.sell_tax_amount,
                    'category_id': get_category_id
                })
        '''按费用生成支出单'''
        if self.clean_cost :
            pay_category_id = self.env.ref('asset.asset_clean_pay').id
            other_money_order = self.env['other.money.order'].create({
                    'state': 'draft',
                    'partner_id': None,
                    'date': self.date,
                    'bank_id': self.bank_account.id,
                    'type': 'other_pay',
                    'context' : 'other_pay'
                })
            self.env['other.money.order.line'].create({
                    'other_money_id': other_money_order.id,
                    'amount': self.clean_cost,
                    'category_id': pay_category_id
                })

        '''生成凭证'''
        vouch_obj = self.env['voucher'].create({'date': self.date})
        if asset.line_ids:
            depreciation2 = sum(line.cost_depreciation for line in asset.line_ids)
        else:
            depreciation2 = 0.0
        depreciation = asset.depreciation_value2 + depreciation2
        income = asset.cost - depreciation
        self.write({'voucher_id': vouch_obj.id})
        '''借方行'''
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'清理固定资产',
                     'debit': income, 'account_id': asset.attribute.clean_costs.id,
                     'auxiliary_id': False
                     })
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'清理固定资产',
                     'debit': depreciation, 'account_id': asset.account_depreciation2.id,
                     'auxiliary_id': False
                     })
        '''贷方行'''
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'清理固定资产',
                     'credit': asset.cost, 'account_id': asset.account_asset.id,
                     'auxiliary_id': False
                     })

class CreateChangWizard(models.TransientModel):
    '''固定资产变更'''
    _name = 'create.chang.wizard'
    _description = 'Create chang Wizard form'

    @api.one
    @api.depends('chang_date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.chang_date)

    chang_date = fields.Date(u'变更日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    chang_cost = fields.Float(u'变更金额', required=True, digits=dp.get_precision(u'金额'))
    chang_depreciation_number = fields.Float(u'变更折旧期间', required=True)
    chang_tax = fields.Float(u'变更税额', digits=dp.get_precision(u'变更税额'), required=True)
    chang_partner_id = fields.Many2one('partner', u'往来单位', ondelete='restrict', required=True)

    @api.one
    def create_chang_account(self):
        asset = self.env['asset'].browse(self.env.context.get('active_id'))
        if self.chang_cost > 0:
            chang_before_cost = asset.cost
            chang_before_depreciation_number = asset.depreciation_number
            asset.cost = self.chang_cost + asset.cost
            asset.surplus_value = asset.cost - asset.depreciation_value2
            asset.tax = asset.tax + self.chang_tax
            """生成凭证"""
            categ = self.env.ref('money.core_category_purchase')
            money_invoice = self.env['money.invoice'].create({
                        'name': u'固定资产变更'+asset.code,
                        'partner_id': self.chang_partner_id.id,
                        'category_id': categ.id,
                        'date': self.chang_date,
                        'amount': self.chang_cost + self.chang_tax,
                        'reconciled': 0,
                        'to_reconcile': self.chang_cost + self.chang_tax,
                        'date_due': fields.Date.context_today(self),
                        'state': 'draft',
                        'tax_amount': self.chang_tax
                })
            chang_account = self.env['voucher.line'].search(['&',('voucher_id', '=', money_invoice.voucher_id.id),('debit', '=', self.chang_cost)])
            chang_account.write({'account_id': asset.account_asset.id})
            self.env['chang.line'].create({'date':self.chang_date,'period_id':self.period_id.id,'chang_before':chang_before_cost,
                                           'chang_after':asset.cost,'chang_name':u'原值变更','order_id':asset.id,'partner_id':self.chang_partner_id.id
            })
        asset.depreciation_number = asset.depreciation_number + self.chang_depreciation_number
        asset.depreciation_value = asset.depreciation_value + asset.attribute.depreciation_value * self.chang_cost / 100
        if self.chang_depreciation_number:
            self.env['chang.line'].create({'date':self.chang_date,'period_id':self.period_id.id,'chang_before':chang_before_depreciation_number,
                                           'chang_after':asset.depreciation_number,'chang_name':u'折旧期间变更','order_id':asset.id,'partner_id':self.chang_partner_id.id
            })

class asset_line(models.Model):
    _name = 'asset.line'
    _description = u'折旧明细'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    order_id = fields.Many2one('asset', u'订单编号', select=True,
                               required=True, ondelete='cascade')
    cost_depreciation = fields.Float(u'每月折旧额', required=True, digits=dp.get_precision(u'金额'))
    no_depreciation = fields.Float(u'未提折旧额')
    code = fields.Char(u'编码')
    name = fields.Char(u'名称')
    date = fields.Date(u'记帐日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)

class CreateDepreciationWizard(models.TransientModel):
    """生成每月折旧的向导 根据输入的期间"""
    _name = "create.depreciation.wizard"

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    date = fields.Date(u'记帐日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    @api.multi
    def create_depreciation(self):
        vouch_obj = self.env['voucher'].create({'date': self.date})
        res = {}
        for asset in self.env['asset'].search([('no_depreciation', '=', False), ('period_id','!=', self.period_id.id)]):
            if self.period_id not in asset.line_ids.period_id:
                cost_depreciation = asset.cost_depreciation
                total = sum(line.cost_depreciation for line in asset.line_ids) + asset.depreciation_value
                if asset.surplus_value <= (total + cost_depreciation):
                    cost_depreciation = asset.surplus_value - total
                    asset.no_depreciation = 1
                '''借方行'''
                if asset.account_depreciation.id not in res:
                    res[asset.account_depreciation.id] = {'debit': 0}
                val = res[asset.account_depreciation.id]
                val.update({'debit':val.get('debit') + cost_depreciation,
                            'voucher_id': vouch_obj.id,
                            'account_id': asset.account_depreciation.id,
                            'name': u'固定资产折旧',
                            })

                '''贷方行'''
                if asset.account_depreciation2.id not in res:
                    res[asset.account_depreciation2.id] = {'credit': 0}

                val = res[asset.account_depreciation2.id]
                val.update({'credit':val.get('credit') + cost_depreciation,
                            'voucher_id': vouch_obj.id,
                            'account_id': asset.account_depreciation2.id,
                            'name': u'固定资产折旧',
                            })
                '''折旧明细行'''
                self.env['asset.line'].create({
                     'date': self.date,
                     'order_id': asset.id,
                     'period_id': self.period_id.id,
                     'cost_depreciation': cost_depreciation,
                     'name':asset.name,
                     'code':asset.code,
                     'no_depreciation':asset.surplus_value - total - cost_depreciation,
                    })

        for account_id,val in res.iteritems():
            self.env['voucher.line'].create(dict(val,account_id = account_id))
            print account_id,val

        if not vouch_obj.line_ids :
            vouch_obj.unlink()
            raise except_orm(u'错误', u'本期所有固定资产都已折旧！')

class chang_line(models.Model):
    _name = 'chang.line'
    _description = u'变更明细'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    order_id = fields.Many2one('asset', u'订单编号', select=True,
                               required=True, ondelete='cascade')
    chang_name = fields.Char(u'变更内容', required=True)
    date = fields.Date(u'记帐日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    chang_before = fields.Float(u'变更前')
    chang_after = fields.Float(u'变更后')
    chang_money_invoice = fields.Many2one('money.invoice', u'对应源单', readonly=True, ondelete='restrict')
    partner_id = fields.Many2one('partner', u'变更单位')
