# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

# 字段只读状态
READONLY_STATES = {
        'done': [('readonly', True)],
        'clean': [('readonly', True)],
    }

class asset_category(models.Model):
    '''固定资产分类'''
    _name = 'asset.category'
    name = fields.Char(u'名称', required=True)
    account_accumulated_depreciation = fields.Many2one(
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
    @api.depends('cost','depreciation_previous')
    def _get_surplus_value(self):
        self.surplus_value = self.cost - self.depreciation_previous
        self.depreciation_value = self.category_id.depreciation_value * self.cost / 100

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
    is_init = fields.Boolean(u'初始化固定资产', states=READONLY_STATES)
    no_depreciation = fields.Boolean(u'不折旧')
    category_id = fields.Many2one('asset.category', u'固定资产分类', ondelete='restrict', required=True, states=READONLY_STATES)
    depreciation_previous = fields.Float(u'以前折旧', digits=dp.get_precision(u'金额'), required=True, states=READONLY_STATES)
    depreciation_number = fields.Float(u'折旧期间数', required=True, states=READONLY_STATES)
    surplus_value = fields.Float(u'残值', digits=dp.get_precision(u'金额'), store=True, compute='_get_surplus_value')
    depreciation_value = fields.Float(u'最终残值', digits=dp.get_precision(u'金额'), required=True, states=READONLY_STATES)
    account_credit = fields.Many2one(
        'finance.account', u'固定资产贷方科目', required=True, states=READONLY_STATES)
    account_depreciation = fields.Many2one(
        'finance.account', u'折旧费用科目', required=True, states=READONLY_STATES)
    account_accumulated_depreciation = fields.Many2one(
        'finance.account', u'累计折旧科目', required=True, states=READONLY_STATES)
    account_asset = fields.Many2one(
        'finance.account', u'固定资产科目', required=True, states=READONLY_STATES)
    cost_depreciation = fields.Float(u'每月折旧额', digits=dp.get_precision(u'金额'), store=True, compute='_get_cost_depreciation')
    line_ids = fields.One2many('asset.line', 'order_id', u'折旧明细行',
                               states=READONLY_STATES, copy=False)
    chang_ids = fields.One2many('chang.line', 'order_id', u'变更明细行',
                               states=READONLY_STATES, copy=False)
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict', copy=False)
    money_invoice = fields.Many2one('money.invoice', u'对应结算单', readonly=True, ondelete='restrict', copy=False)
    other_money_order = fields.Many2one('other.money.order', u'对应其他应付款单', readonly=True, ondelete='restrict', copy=False)

    @api.onchange('category_id')
    def onchange_category_id(self):
        '''当固定资产分类发生变化时，折旧期间数，固定资产科目，累计折旧科目，最终残值同时变化'''
        if self.category_id:
            self.depreciation_number = self.category_id.depreciation_number
            self.account_asset = self.category_id.account_asset
            self.account_accumulated_depreciation = self.category_id.account_accumulated_depreciation
            self.account_depreciation = self.category_id.account_depreciation
            self.depreciation_value = self.category_id.depreciation_value * self.cost / 100

    @api.onchange('cost')
    def onchange_cost(self):
        '''当固定资产金额发生变化时，最终残值，价格合计,残值，每月折旧额变化'''
        if self.cost:
            self.depreciation_value = self.category_id.depreciation_value * self.cost / 100

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''当合作伙伴发生变化时，固定资产贷方科目变化'''
        if self.partner_id:
            self.account_credit = self.partner_id.s_category_id.account_id

    @api.onchange('bank_account')
    def onchange_bank_account(self):
        '''当结算帐户发生变化时，固定资产贷方科目变化'''
        if self.bank_account:
            self.account_credit = self.bank_account.account_id

    @api.one
    def _wrong_asset_done(self):
        if self.state == 'done':
            raise UserError(u'请不要重复审核！')
        if self.period_id.is_closed:
            raise UserError(u'该会计期间(%s)已结账！不能审核'%self.period_id.name)
        if self.cost <= 0:
            raise UserError(u'金额必须大于0！\n金额:%s'%self.cost)
        if self.tax < 0:
            raise UserError(u'税额必须大于0！\n税额:%s'%self.tax)
        if self.depreciation_previous < 0:
            raise UserError(u'以前折旧必须大于0！\n折旧金额:%s' % self.depreciation_previous)
        return

    @api.one
    def _partner_generate_invoice(self):
        ''' 赊购的方式，选择往来单位时，生成结算单 '''
        categ = self.env.ref('money.core_category_purchase')
        money_invoice = self.env['money.invoice'].create({
                'name': u'固定资产'+self.code,
                'partner_id': self.partner_id.id,
                'category_id': categ and categ.id,
                'date': self.date,
                'amount': self.amount,
                'reconciled': 0,
                'to_reconcile': self.amount,
                'date_due': fields.Date.context_today(self),
                'state': 'draft',
                'tax_amount': self.tax
        })
        self.write({'money_invoice': money_invoice.id})
        '''变化科目'''
        chang_account = self.env['voucher.line'].search(['&',
            ('voucher_id', '=', money_invoice.voucher_id.id),
            ('debit', '=', self.cost)])
        chang_account.write({'account_id': self.account_asset.id})
        return money_invoice

    @api.one
    def _bank_account_generate_other_pay(self):
        ''' 现金和银行支付的方式，选择结算账户，生成其他支出单 '''
        category = self.env.ref('asset.asset')
        other_money_order = self.with_context(type='other_pay').env['other.money.order'].create({
            'state': 'draft',
            'partner_id': self.partner_id.id,
            'date': self.date,
            'bank_id': self.bank_account.id,
        })
        self.write({'other_money_order': other_money_order.id})
        self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id ,
            'amount': self.cost ,
            'tax_rate': self.cost and self.tax / self.cost * 100 or 0,
            'tax_amount' : self.tax,
            'category_id': category and category.id
        })
        return other_money_order

    @api.one
    def _construction_generate_voucher(self):
        ''' 贷方科目选择在建工程，直接生成凭证 '''
        vals = {}
        vouch_obj = self.env['voucher'].create({'date': self.date})
        self.write({'voucher_id': vouch_obj.id})
        vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'string': u'固定资产',
             'amount': self.amount, 'credit_account_id': self.account_credit.id,
             'debit_account_id': self.account_asset.id, 'partner_credit': self.partner_id.id, 'partner_debit': '',
             'buy_tax_amount': self.tax or 0
             })
        self.env['money.invoice'].create_voucher_line(vals)
        vouch_obj.voucher_done()
        return vouch_obj

    @api.one
    def asset_done(self):
        ''' 审核固定资产 '''
        self._wrong_asset_done()
        # 非初始化固定资产生成凭证
        if not self.is_init:
            if self.partner_id and self.partner_id.s_category_id.account_id == self.account_credit:
                self._partner_generate_invoice()
            elif self.bank_account and self.account_credit == self.bank_account.account_id:
                self._bank_account_generate_other_pay()
            else:
                self._construction_generate_voucher()

        self.state = 'done'

    @api.one
    def asset_draft(self):
        ''' 反审核固定资产 '''
        if self.state == 'draft':
            raise UserError(u'请不要重复反审核！')
        if self.line_ids:
            raise UserError(u'已折旧不能反审核！')
        if self.chang_ids:
            raise UserError(u'已变更不能反审核！')
        if self.period_id.is_closed:
            raise UserError(u'该会计期间(%s)已结账！不能反审核'%self.period_id.name)
        self.state = 'draft'
        '''删掉凭证'''
        if self.voucher_id:
            voucher, self.voucher_id = self.voucher_id, False
            if voucher.state == 'done':
                voucher.voucher_draft()
            voucher.unlink()
        '''删掉其他应付款单'''
        if self.other_money_order:
            other_money_order, self.other_money_order = self.other_money_order, False
            if other_money_order.state == 'done':
                other_money_order.other_money_draft()
            other_money_order.unlink()
        '''删掉结算单'''
        if self.money_invoice:
            money_invoice, self.money_invoice = self.money_invoice, False
            if money_invoice.state == 'done':
                money_invoice.money_invoice_draft()
            money_invoice.unlink()

    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(u'只能删除草稿状态的固定资产')

        return super(asset, self).unlink()


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
    def _generate_other_get(self):
        '''按发票收入生成收入单'''
        get_category = self.env.ref('asset.asset_clean_get')
        other_money_order = self.with_context(type='other_get').env['other.money.order'].create({
                    'state': 'draft',
                    'partner_id': None,
                    'date': self.date,
                    'bank_id': self.bank_account.id,
                })
        self.env['other.money.order.line'].create({
                    'other_money_id': other_money_order.id,
                    'amount': self.residual_income,
                    'tax_rate': self.residual_income and self.sell_tax_amount / self.residual_income * 100 or 0,
                    'tax_amount' : self.sell_tax_amount,
                    'category_id': get_category and get_category.id
                })
        return other_money_order

    @api.one
    def _clean_cost_generate_other_pay(self, clean_cost):
        '''按费用生成支出单'''
        pay_category = self.env.ref('asset.asset_clean_pay')
        other_money_order = self.with_context(type='other_pay').env['other.money.order'].create({
                'state': 'draft',
                'partner_id': None,
                'date': self.date,
                'bank_id': self.bank_account.id,
            })
        self.env['other.money.order.line'].create({
                'other_money_id': other_money_order.id,
                'amount': clean_cost,
                'category_id': pay_category and pay_category.id
            })

    @api.one
    def _generate_voucher(self, asset):
        ''' 生成凭证，并审核 '''
        vouch_obj = self.env['voucher'].create({'date': self.date})
        depreciation2 = sum(line.cost_depreciation for line in asset.line_ids)
        depreciation = asset.depreciation_previous + depreciation2
        income = asset.cost - depreciation
        asset.write({'voucher_id': vouch_obj.id})
        '''借方行'''
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'清理固定资产',
                     'debit': income, 'account_id': asset.category_id.clean_costs.id,
                     'auxiliary_id': False
                     })
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'清理固定资产',
                     'debit': depreciation, 'account_id': asset.account_accumulated_depreciation.id,
                     'auxiliary_id': False
                     })
        '''贷方行'''
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'清理固定资产',
                     'credit': asset.cost, 'account_id': asset.account_asset.id,
                     'auxiliary_id': False
                     })
        vouch_obj.voucher_done()
        return vouch_obj

    @api.one
    def create_clean_account(self):
        ''' 清理固定资产 '''
        if not self.env.context.get('active_id'):
            return
        asset = self.env['asset'].browse(self.env.context.get('active_id'))
        asset.no_depreciation = 1
        asset.state = 'clean'
        # 按发票收入生成收入单
        self._generate_other_get()
        # 按费用生成支出单
        if self.clean_cost:
            self._clean_cost_generate_other_pay(self.clean_cost)
        # 生成凭证
        self._generate_voucher(asset)

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
        if not self.env.context.get('active_id'):
            return
        asset = self.env['asset'].browse(self.env.context.get('active_id'))
        if self.chang_cost > 0:
            chang_before_cost = asset.cost
            chang_before_depreciation_number = asset.depreciation_number
            asset.cost = self.chang_cost + asset.cost
            asset.surplus_value = asset.cost - asset.depreciation_previous
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
        asset.depreciation_value = asset.depreciation_value + asset.category_id.depreciation_value * self.chang_cost / 100
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
    def _get_voucher_line(self, asset, cost_depreciation, vouch_obj):
        '''借方行'''
        res = {}
        if asset.account_depreciation.id not in res:
            res[asset.account_depreciation.id] = {'debit': 0}
        val = res[asset.account_depreciation.id]
        val.update({'debit': val.get('debit') + cost_depreciation,
                    'voucher_id': vouch_obj.id,
                    'account_id': asset.account_depreciation.id,
                    'name': u'固定资产折旧',
                    })

        '''贷方行'''
        if asset.account_accumulated_depreciation.id not in res:
            res[asset.account_accumulated_depreciation.id] = {'credit': 0}

        val = res[asset.account_accumulated_depreciation.id]
        val.update({'credit': val.get('credit') + cost_depreciation,
                    'voucher_id': vouch_obj.id,
                    'account_id': asset.account_accumulated_depreciation.id,
                    'name': u'固定资产折旧',
                    })
        return res

    @api.multi
    def _generate_asset_line(self, asset, cost_depreciation, total):
        '''生成折旧明细行'''
        asset_line = self.env['asset.line'].create({
             'date': self.date,
             'order_id': asset.id,
             'period_id': self.period_id.id,
             'cost_depreciation': cost_depreciation,
             'name': asset.name,
             'code': asset.code,
             'no_depreciation': asset.surplus_value - total - cost_depreciation,
            })
        return asset_line

    @api.multi
    def create_depreciation(self):
        ''' 资产折旧，生成凭证和折旧明细'''

        vouch_obj = self.env['voucher'].create({'date': self.date})
        res = {}
        asset_line_id_list = []
        for asset in self.env['asset'].search([('no_depreciation', '=', False),
                                               ('state', '=', 'done'), ('period_id', '!=', self.period_id.id)]):
            if self.period_id not in [line.period_id for line in asset.line_ids] and \
                     self.env['finance.period'].period_compare(self.period_id,asset.period_id) > 0:
                cost_depreciation = asset.cost_depreciation
                total = sum(line.cost_depreciation for line in asset.line_ids) + asset.depreciation_value
                if asset.surplus_value <= (total + cost_depreciation):
                    cost_depreciation = asset.surplus_value - total
                    asset.no_depreciation = 1
                # 获得凭证明细行
                res = self._get_voucher_line(asset, cost_depreciation, vouch_obj)
                # 生成折旧明细行
                asset_line_row = self._generate_asset_line(asset, cost_depreciation, total)
                asset_line_id_list.append(asset_line_row.id)
        for account_id,val in res.iteritems():
            self.env['voucher.line'].create(dict(val,account_id = account_id))

        if not vouch_obj.line_ids:
            vouch_obj.unlink()
            raise UserError(u'本期没有需要折旧的固定资产啦！')
        vouch_obj.voucher_done()
        view = self.env.ref('asset.asset_line_tree')
        return {
            'view_mode': 'tree',
            'name': u'资产折旧明细行',
            'views': [(view.id, 'tree')],
            'res_model': 'asset.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', asset_line_id_list)]
        }

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
    chang_money_invoice = fields.Many2one('money.invoice', u'对应结算单', readonly=True, ondelete='restrict')
    partner_id = fields.Many2one('partner', u'变更单位')

class voucher(models.Model):
    _inherit = 'voucher'

    @api.one
    def init_asset(self):
        '''删除以前引入的固定资产内容'''
        for line in self.line_ids:
            if line.init_obj == 'asset':
                line.unlink()

        '''引入固定资产初始化单据'''
        res = {}
        for asset in self.env['asset'].search([('is_init', '=', True)]):
            cost = asset.cost
            depreciation_previous = asset.depreciation_previous
            '''固定资产'''
            if asset.account_asset.id not in res:
                res[asset.account_asset.id] = {'credit':0,'debit': 0} # vorcher_line 没有这个字段 ,'cate':'asset'

            val = res[asset.account_asset.id]
            val.update({'debit':val.get('debit') + cost,
                        'account_id': asset.account_asset.id,
                        'voucher_id': self.id,
                        'init_obj': 'asset',
                        'name': '固定资产 期初'
                        })
            '''累计折旧'''
            if asset.account_accumulated_depreciation.id not in res:
                res[asset.account_accumulated_depreciation.id] = {'credit':0,'debit': 0} # vorcher_line 没有这个字段 ,'cate':'asset'

            val = res[asset.account_accumulated_depreciation.id]
            val.update({'credit':val.get('credit') + depreciation_previous,
                        'account_id': asset.account_accumulated_depreciation.id,
                        'voucher_id': self.id,
                        'init_obj': 'asset',
                        'name': '固定资产 期初'
                        })

        for account_id,val in res.iteritems():
            self.env['voucher.line'].create(dict(val,account_id = account_id),
                                            )
