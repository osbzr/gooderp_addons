# -*- coding: utf-8 -*-

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError
from datetime import datetime

# 字段只读状态
READONLY_STATES = {
        'done': [('readonly', True)],
    }

class asset_attribute(models.Model):
    '''固定资产分类'''
    _name = 'asset_attribute'
    name = fields.Char(u'名称', required=True)
    account_depreciation2 = fields.Many2one(
        'finance.account', u'累计折旧科目', required=True)
    account_asset = fields.Many2one(
        'finance.account', u'固定资产科目', required=True)
    account_depreciation = fields.Many2one(
        'finance.account', u'折旧科目', required=True)
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

    code = fields.Char(u'编码', required="1")
    date = fields.Date(u'记帐日期', required=True)
    name = fields.Char(u'名称', required=True)
    att_count = fields.Integer(u'附单据', default=1)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已审核'),
                              ('clean', u'已清理')], u'状态', default='draft')
    cost = fields.Float(u'金额', digits=dp.get_precision(u'金额'), required=True)
    tax = fields.Float(u'税额', digits=dp.get_precision(u'税额'), required=True)
    money = fields.Float(u'价税合计', digits=dp.get_precision(u'金额'), store=True)
    partner_id = fields.Many2one('partner', u'往来单位', ondelete='restrict')
    goods_id = fields.Many2one('goods', u'商品', ondelete='restrict')
    other_system = fields.Boolean(u'初始化固定资产')
    no_depreciation = fields.Boolean(u'不折旧')
    attribute = fields.Many2one('asset_attribute', u'固定资产分类', ondelete='restrict', required=True)
    depreciation_value2 = fields.Float(u'以前折旧', digits=dp.get_precision(u'金额'), required=True)
    depreciation_number = fields.Float(u'折旧期间数', required=True)
    surplus_value = fields.Float(u'残值', digits=dp.get_precision(u'金额'), required=True)
    depreciation_value = fields.Float(u'最终残值', digits=dp.get_precision(u'金额'), required=True)
    account_credit = fields.Many2one(
        'finance.account', u'固定资产贷方科目', required=True)
    account_depreciation = fields.Many2one(
        'finance.account', u'折旧科目', required=True)
    account_depreciation2 = fields.Many2one(
        'finance.account', u'累计折旧科目', required=True)
    account_asset = fields.Many2one(
        'finance.account', u'固定资产科目', required=True)
    cost_depreciation = fields.Float(u'每月折旧额', required=True, digits=dp.get_precision(u'金额'))
    line_ids = fields.One2many('asset.line', 'order_id', u'折旧明细行',
                               states=READONLY_STATES, copy=True)
    chang_ids = fields.One2many('chang.line', 'order_id', u'变更明细行',
                               states=READONLY_STATES, copy=True)

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
            self.money = self.cost + self.tax
            self.surplus_value = self.cost - self.depreciation_value2
            self.cost_depreciation = (self.surplus_value - self.depreciation_value ) / self.depreciation_number
    @api.one
    @api.onchange('depreciation_value2')
    def onchange_depreciation_value2(self):
        '''当固定资产期初发生变化时，残值，每月折旧额变化'''
        if self.depreciation_value2:
            self.surplus_value = self.cost - self.depreciation_value2
            self.cost_depreciation = (self.surplus_value - self.depreciation_value) / self.depreciation_number

    @api.one
    @api.onchange('depreciation_number')
    def onchange_depreciation_number(self):
        '''当固定资产折旧期间数发生变化时，每月折旧额变化'''
        if self.depreciation_number:
           self.cost_depreciation = (self.surplus_value - self.depreciation_value) / self.depreciation_number

    @api.one
    @api.onchange('depreciation_value')
    def onchange_depreciation_value(self):
        '''当固定资产最终残值发生变化时，每月折旧额变化'''
        if self.depreciation_value:
           self.cost_depreciation = (self.surplus_value - self.depreciation_value) / self.depreciation_number

    @api.one
    @api.onchange('tax')
    def onchange_tax(self):
        '''当固定资产金额发生变化时，价格合计变化'''
        if self.tax:
            self.money = self.cost + self.tax

    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict')

    @api.one
    def asset_done(self):
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        if self.period_id.is_closed is True:
            raise except_orm(u'错误', u'该会计期间已结账！不能审核')
        if self.cost <= 0 :
            raise except_orm(u'错误', u'金额必须大于0！')
        if self.tax < 0 :
            raise except_orm(u'错误', u'金额必须大于0！')
        if self.depreciation_value2 < 0 :
            raise except_orm(u'错误', u'金额必须大于0！')
        '''非初始化固定资产生成凭证'''

        if not self.other_system :
            vals = {}
            vouch_obj = self.env['voucher'].create({'date': self.date})
            self.write({'voucher_id': vouch_obj.id})
            vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'string': u'固定资产',
                     'amount': self.money, 'credit_account_id': self.account_credit.id,
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
        voucher, self.voucher_id = self.voucher_id, False
        voucher.unlink()
        self.state = 'draft'


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
    account_income = fields.Many2one(
        'finance.account', u'收入科目', required=True)

    @api.one
    def create_clean_account(self):
        asset = self.env['asset'].browse(self.env.context.get('active_id'))
        asset.no_depreciation = 1
        asset.state = 'clean'
        vouch_obj = self.env['voucher'].create({'date': self.date})
        if asset.line_ids:
            depreciation2 = sum(line.cost_depreciation for line in asset.line_ids)
        else:
            depreciation2 = 0.0
        depreciation = asset.depreciation_value2 + depreciation2
        income = self.residual_income - self.clean_cost
        difference = income + depreciation - asset.cost - self.sell_tax_amount
        '''生成凭证'''
        self.write({'voucher_id': vouch_obj.id})
        '''借方行'''
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'清理固定资产',
                     'debit': income, 'account_id': self.account_income.id,
                     'partner_id': asset.partner_id.id or '', 'auxiliary_id': False
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
        if self.sell_tax_amount:
            if not self.env.user.company_id.output_tax_account:
                raise except_orm(u'错误', u'请通过"配置-->高级配置-->系统参数"菜单来设置销项税科目' )
            self.env['voucher.line'].create({
                'name': u'清理固定资产',
                'account_id': self.env.user.company_id.output_tax_account.id, 'credit': self.sell_tax_amount, 'voucher_id': vouch_obj.id
        })
        '''营业外收入还是营业外支出'''
        if difference:
            if difference > 0:
                self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'清理固定资产',
                     'credit': difference, 'account_id': asset.attribute.clean_income.id,
                     'auxiliary_id': False
                     })
            else:
                self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'清理固定资产',
                     'debit': abs(difference), 'account_id': asset.attribute.clean_costs.id,
                     'auxiliary_id': False
                     })

class CreateChangWizard(models.TransientModel):
    '''固定资产变更'''
    _name = 'create.chang.wizard'
    _description = 'Create chang Wizard form'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    date = fields.Date(u'变更日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    chang_cost = fields.Float(u'变更金额', required=True, digits=dp.get_precision(u'金额'))
    chang_depreciation_number = fields.Float(u'变更折旧期间', required=True)
    chang_tax = fields.Float(u'变更税额', digits=dp.get_precision(u'变更税额'), required=True)
    chang_account = fields.Many2one('finance.account', u'贷方应付科目', required=True)
    partner_id = fields.Many2one('partner', u'往来单位', ondelete='restrict')

    @api.one
    def create_chang_account(self):
        asset = self.env['asset'].browse(self.env.context.get('active_id'))
        if self.chang_cost > 0:
            chang_before_cost = asset.cost
            chang_before_depreciation_number = asset.depreciation_number
            asset.cost = self.chang_cost + asset.cost
            asset.surplus_value = asset.cost - asset.depreciation_value2
            asset.tax = asset.tax + self.chang_tax
            asset.depreciation_value = asset.attribute.depreciation_value * asset.cost / 100
            """生成凭证"""
            vals = {}
            vouch_obj = self.env['voucher'].create({'date': self.date})
            self.write({'voucher_id': vouch_obj.id})
            vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.date, 'string': u'固定资产变更',
                     'amount': self.chang_cost, 'credit_account_id': self.chang_account.id,
                     'debit_account_id': asset.account_asset.id, 'partner_credit': self.partner_id.id, 'partner_debit': '',
                     'buy_tax_amount': self.chang_tax or 0
                     })
            self.env['money.invoice'].create_voucher_line(vals)
            self.env['chang.line'].create({'date':self.date,'period_id':self.period_id.id,'chang_before':chang_before_cost,
                                           'chang_after':asset.cost,'chang_name':u'原值变更','order_id':asset.id
            })
        asset.depreciation_number = asset.depreciation_number + self.chang_depreciation_number
        asset.cost_depreciation = (asset.surplus_value - asset.depreciation_value ) / asset.depreciation_number
        if self.chang_depreciation_number:
            self.env['chang.line'].create({'date':self.date,'period_id':self.period_id.id,'chang_before':chang_before_depreciation_number,
                                           'chang_after':asset.depreciation_number,'chang_name':u'折旧期间变更','order_id':asset.id
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

    """同一会计期间不能多次折旧
    _sql_constraints = [
        ('period_uniq', 'unique (period_id)', u'同一会计期间不能多次折旧'),
    ]
    """



class CreateDepreciationWizard(models.TransientModel):
    """生成每月折旧的向导 根据输入的期间"""
    _name = "create.depreciation.wizard"
    period_id = fields.Many2one('finance.period', string=u'会计期间')

    @api.multi
    def create_depreciation(self):
        vouch_obj = self.env['voucher'].create({'date': fields.Date.context_today(self)})
        self.write({'voucher_id': vouch_obj.id})
        res = {}
        for asset in self.env['asset'].search([('no_depreciation', '=', False)]):
            cost_depreciation = asset.cost_depreciation
            total = sum(line.cost_depreciation for line in asset.line_ids) + asset.depreciation_value
            if asset.surplus_value <= (total + cost_depreciation):
                cost_depreciation = asset.surplus_value - total
                asset.no_depreciation = 1
                asset.line_ids.no_depreciation = total
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
                 'order_id': asset.id,
                 'date': fields.Date.context_today(self),
                 'cost_depreciation': cost_depreciation,
                 'name':asset.name,
                 'code':asset.code,
                 'no_depreciation':asset.surplus_value - total - cost_depreciation
                                          })

        for account_id,val in res.iteritems():
            self.env['voucher.line'].create(dict(val,account_id = account_id))
            print account_id,val

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

