# -*- coding: utf-8 -*-

from datetime import datetime

import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],  # 已确认
    'clean': [('readonly', True)],  # 已处置
    'deficit': [('readonly', True)],  # 盘亏
}

error_code = ['1001', '1002', '1009']

class AssetCategory(models.Model):
    '''固定资产分类'''
    _name = 'asset.category'
    _description = u'固定资产分类'

    # 字段，命名问题很严重
    name = fields.Char(u'名称', required=True)
    # 一些带到固定资产上的默认值
    is_depreciation = fields.Boolean(u'永不折旧', default=False)
    asset_other_money_pay_category = fields.Many2one(
        'core.category', u'类别', domain="[('type','=','other_pay')]")
    account_accumulated_depreciation = fields.Many2one(
        'finance.account', u'累计折旧科目', domain="[('account_type','=','normal')]")
    account_asset = fields.Many2one(
        'finance.account', u'固定资产科目', domain="[('account_type','=','normal')]")
    account_depreciation = fields.Many2one(
        'finance.account', u'折旧费用科目', domain="[('account_type','=','normal')]")
    depreciation_number = fields.Float(u'折旧期间数')
    depreciation_value = fields.Float(u'最终残值率%')
    clean_income = fields.Many2one(
        'finance.account', u'固定资产处置收入科目', domain="[('account_type','=','normal')]")
    clean_costs = fields.Many2one(
        'finance.account', u'固定资产处置成本科目', domain="[('account_type','=','normal')]")
    # 用于软删除归档
    active = fields.Boolean(u'启用', default=True)
    clear_account_id = fields.Many2one(
        'finance.account', u'固定资产处置科目', domain="[('account_type','=','normal')]")
    # 未来支持多公司
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

class Asset(models.Model):
    _name = 'asset'
    _description = u'固定资产'
    _order = "code"  # 按资产编号排序

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        ''' 根据入账日期获取期间，用于生成凭证 '''
        self.period_id = self.env['finance.period'].get_period(self.date)

    @api.one
    @api.depends('cost', 'tax')
    def _get_amount(self):
        ''' 价税合计 '''
        self.amount = self.cost + self.tax

    @api.one
    @api.depends('cost', 'depreciation_previous')
    def _get_surplus_value(self):
        ''' 计算固定资产原值和残值 '''
        # 原值 = 购置成本 - （ERP系统上线前）已提折旧
        self.surplus_value = self.cost - self.depreciation_previous
        # 残值按固定资产分类上的残值比率计算
        self.depreciation_value = self.category_id.depreciation_value * self.cost / 100

    @api.one
    @api.depends('surplus_value', 'depreciation_value', 'depreciation_number', 'no_depreciation')
    def _get_cost_depreciation(self):
        ''' 计算每月折旧 '''
        if self.no_depreciation == True:  # 不提折旧不要算
            self.cost_depreciation = 0
        else:  # 原值减残值减已折旧额，再除以剩余折旧期数
            dep_his_count = 0  # 已提期数
            dep_his_amount = 0  # 已提折旧
            for l in self.line_ids:
                dep_his_amount += l.cost_depreciation
                dep_his_count += 1
            if dep_his_count == self.depreciation_number:
                self.cost_depreciation = 0  # 已提完
            else:
                self.cost_depreciation = (self.surplus_value - self.depreciation_value
                                          - dep_his_amount) \
                                         / (self.depreciation_number - dep_his_count)

    @api.one
    @api.depends('surplus_value', 'line_ids', 'state')
    def _get_net_value(self):
        ''' 计算固定资产净值 '''
        if self.state == 'clean':  # 已处置的固定资产净值为0
            self.net_value = 0
        else:  # 原值 - 折旧
            self.net_value = self.surplus_value - sum(
                [l.cost_depreciation for l in self.line_ids])

    # 字段
    code = fields.Char(u'编号', required="1", states=READONLY_STATES)
    name = fields.Char(u'名称', required=True, states=READONLY_STATES)
    category_id = fields.Many2one(
        'asset.category', u'固定资产分类', ondelete='restrict', required=True, states=READONLY_STATES)
    cost = fields.Float(u'金额', digits=dp.get_precision(
        'Amount'), required=True, states=READONLY_STATES)
    surplus_value = fields.Float(u'原值', digits=dp.get_precision(
        'Amount'), store=True, compute='_get_surplus_value')

    net_value = fields.Float(u'净值', digits=dp.get_precision(
        'Amount'), store=True, compute='_get_net_value')
    no_depreciation = fields.Boolean(u'暂停折旧')
    depreciation_number = fields.Integer(
        u'折旧期间数', states=READONLY_STATES)
    depreciation_value = fields.Float(u'最终残值', digits=dp.get_precision(
        'Amount'), states=READONLY_STATES)
    cost_depreciation = fields.Float(u'每月折旧额', digits=dp.get_precision(
        'Amount'), store=True, compute='_get_cost_depreciation')
    forever_no_depreciation = fields.Boolean(u'永不折旧')

    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已确认'),
                              ('clean', u'已处置'),
                              ('deficit', u'已盘亏')], u'状态', default='draft',
                             index=True, )

    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    date = fields.Date(u'记账日期', required=True, states=READONLY_STATES)
    tax = fields.Float(u'税额', digits=dp.get_precision(
        'Amount'), required=True, states=READONLY_STATES)
    amount = fields.Float(u'价税合计', digits=dp.get_precision(
        'Amount'), store=True, compute='_get_amount')
    is_init = fields.Boolean(u'初始化资产', states=READONLY_STATES,
                             help=u'此固定资产在ERP系统启用前就已经有折旧了')
    depreciation_previous = fields.Float(u'以前折旧', digits=dp.get_precision(
        'Amount'), required=True, states=READONLY_STATES)
    account_asset = fields.Many2one(
        'finance.account', u'固定资产科目', required=True, states=READONLY_STATES, domain="[('account_type','=','normal')]")
    account_depreciation = fields.Many2one(
        'finance.account', u'折旧费用科目', states=READONLY_STATES, domain="[('account_type','=','normal')]")
    account_accumulated_depreciation = fields.Many2one(
        'finance.account', u'累计折旧科目', states=READONLY_STATES, domain="[('account_type','=','normal')]")

    line_ids = fields.One2many('asset.line', 'order_id', u'折旧明细行',
                               states=READONLY_STATES, copy=False)
    chang_ids = fields.One2many('chang.line', 'order_id', u'变更明细行',
                                states=READONLY_STATES, copy=False)
    attachment_number = fields.Integer(compute='_compute_attachment_number', string=u'附件号')

    # 界面上不可见的字段
    voucher_id = fields.Many2one(
        'voucher', u'对应凭证', readonly=True, ondelete='restrict', copy=False)
    money_invoice = fields.Many2one(
        'money.invoice', u'对应结算单', readonly=True, ondelete='restrict', copy=False)
    other_money_order = fields.Many2one(
        'other.money.order', u'对应其他应付款单', readonly=True, ondelete='restrict', copy=False)
    # 未来支持多公司
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.onchange('category_id')
    def onchange_category_id(self):
        '''当固定资产分类发生变化时，折旧期间数，固定资产科目，累计折旧科目，最终残值同时变化'''
        if self.category_id:
            self.depreciation_number = self.category_id.depreciation_number
            self.account_asset = self.category_id.account_asset
            self.account_accumulated_depreciation = self.category_id.account_accumulated_depreciation
            self.account_depreciation = self.category_id.account_depreciation
            self.depreciation_value = self.category_id.depreciation_value * self.cost / 100
            self.forever_no_depreciation = self.category_id.is_depreciation

    @api.onchange('forever_no_depreciation')
    def onchange_no_depreciation(self):
        # 当选择了收支项后，则自动填充上类别和金额
        self.no_depreciation = self.forever_no_depreciation

    @api.onchange('cost')
    def onchange_cost(self):
        '''当固定资产金额发生变化时，最终残值变化'''
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

    @api.onchange('is_init')
    def onchange_is_init(self):
        # 变更IS_INIT后 以前折旧 重写为0
        if not self.is_init:
            self.depreciation_previous = 0

    @api.one
    def _wrong_asset_done(self):
        ''' 固定资产确认入账前的验证 '''
        if self.state == 'done':
            raise UserError(u'请不要重复确认！')
        if self.period_id.is_closed:
            raise UserError(u'该会计期间(%s)已结账！不能确认' % self.period_id.name)
        if self.cost <= 0:
            raise UserError(u'金额必须大于0！\n金额:%s' % self.cost)
        if self.tax < 0:
            raise UserError(u'税额必须大于0！\n税额:%s' % self.tax)
        if self.depreciation_previous < 0:
            raise UserError(u'以前折旧必须大于0！\n折旧金额:%s' %
                            self.depreciation_previous)

    @api.one
    def _partner_generate_invoice(self):
        ''' 赊购的方式，选择往来单位时，生成结算单 '''
        categ = self.env.ref('asset.asset_expense')  # 固定资产采购
        # 创建结算单
        money_invoice = self.env['money.invoice'].create({
            'name': u'固定资产' + self.code,
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

        ''' 因分类上只能设置一个固定资产科目，这里要用当前固定资产的对应科目替换凭证 '''

        # 如未自动确认，则确认一下结算单
        if money_invoice.state != 'done':
            money_invoice.money_invoice_done()
        # 找到结算单对应的凭证行并修改科目
        chang_account = self.env['voucher.line'].search(
            [('voucher_id', '=', money_invoice.voucher_id.id),
             ('account_id', '=', categ.account_id.id)])
        chang_account.write({'account_id': self.account_asset.id})

        return money_invoice

    @api.one
    def _bank_account_generate_other_pay(self):
        ''' 现金和银行支付的方式，选择结算账户，生成其他支出单 '''
        category = self.env.ref('asset.asset')  # 借：固定资产
        other_money_order = self.with_context(type='other_pay', modify_from_webclient=True).env['other.money.order'].create({
            'state': 'draft',
            'partner_id': self.partner_id.id,
            'date': self.date,
            'bank_id': self.bank_account.id,
        })
        self.write({'other_money_order': other_money_order.id})
        other_money_order_line = self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id,
            'amount': self.cost,
            'tax_rate': self.cost and self.tax / self.cost * 100 or 0,
            'tax_amount': self.tax,
            'category_id': category and category.id
        })
        #other_money_order_line.onchange_category_id()
        other_money_order.other_money_done()
        return other_money_order

    @api.one
    def _construction_generate_voucher(self):
        ''' 贷方科目选择在建工程，直接生成凭证 '''
        vals = {}
        vouch_obj = self.env['voucher'].create({'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        self.write({'voucher_id': vouch_obj.id})
        vals.update({'vouch_obj_id': vouch_obj.id, 'string': self.name, 'name': u'固定资产',
                     'amount': self.amount, 'credit_account_id': self.account_credit.id,
                     'debit_account_id': self.account_asset.id,
                     'buy_tax_amount': self.tax or 0
                     })
        self.env['money.invoice'].create_voucher_line(vals)
        vouch_obj.voucher_done()

        return vouch_obj

    @api.one
    def asset_done(self):
        ''' 确认固定资产 '''
        self._wrong_asset_done()
        self.state = 'done'
        return True

    @api.one
    def asset_draft(self):
        ''' 撤销确认固定资产 '''
        if self.state == 'draft':
            raise UserError(u'请不要重复撤销确认！')
        if self.line_ids:
            raise UserError(u'已折旧不能撤销确认！')
        if self.chang_ids:
            raise UserError(u'已变更不能撤销确认！')
        if self.period_id.is_closed:
            raise UserError(u'该会计期间(%s)已结账！不能撤销确认' % self.period_id.name)

        '''删掉凭证'''
        if self.voucher_id:
            Voucher, self.voucher_id = self.voucher_id, False
            if Voucher.state == 'done':
                Voucher.voucher_draft()
            Voucher.unlink()
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

        self.state = 'draft'
        return True

    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(u'只能删除草稿状态的固定资产')

        return super(Asset, self).unlink()


class CreateCleanWizard(models.TransientModel):
    '''固定资产处置'''
    _name = 'create.clean.wizard'
    _description = u'固定资产处置向导'

    CLEAN_TYPE = [('guazhang', u'盘亏'),
                  ('handle', u'处置')]

    SELECT = [('bank', u'现金/银行'),
              ('account', '科目')]

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        ''' 根据处置日期取得期间 '''
        self.period_id = self.env['finance.period'].get_period(self.date)

    # 字段
    clean_type = fields.Selection(CLEAN_TYPE, u'操作类型',
                                  required=True,
                                  default='guazhang')
    date = fields.Date(u'日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    # 挂帐科目
    clean_account = fields.Many2one(
        'finance.account', u'固定资产盘亏科目', domain="[('account_type','=','normal')]")
    # 处置支出
    cost_select = fields.Selection(SELECT, u'处置费用类型',
                                   required=True,
                                   default='bank')
    clean_cost = fields.Float(u'处置费用金额')
    cost_bank = fields.Many2one('bank.account', u'处置费用结算账户')
    cost_account = fields.Many2one('finance.account', u'处置费用结算科目', domain="[('account_type','=','normal')]")
    # 处置收入
    income_select = fields.Selection(SELECT, u'残值收入类型',
                                     required=True,
                                     default='bank')
    residual_income = fields.Float(u'残值收入金额')
    sell_tax_amount = fields.Float(u'销项税额')
    income_bank = fields.Many2one('bank.account', u'残值收入结算账户')
    income_account = fields.Many2one('finance.account', u'残值收入结算科目', domain="[('account_type','=','normal')]")
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.one
    def _generate_other_get(self, Asset):
        '''按发票收入生成收入单'''
        if self.bank_account and self.bank_account.account_id.currency_id:
            raise UserError(u'系统占不支持外币结算固定资产')
        get_category = self.env.ref('asset.asset_clean_get')
        other_money_order = self.with_context(type='other_get', modify_from_webclient=True).env['other.money.order'].create({
            'state': 'draft',
            'partner_id': None,
            'date': self.date,
            'bank_id': self.bank_account.id,
        })
        other_money_order_line = self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id,
            'amount': self.residual_income,
            'tax_rate': self.residual_income and self.sell_tax_amount / self.residual_income * 100 or 0,
            'tax_amount': self.sell_tax_amount,
            'category_id': get_category and get_category.id
        })
        #other_money_order_line.onchange_category_id()
        other_money_order.other_money_done()
        # 增加变更行，以后需要可以跟据此行做反向处理
        self.env['chang.line'].create({'date': self.date,
                                       'period_id': self.period_id.id,
                                       'chang_name': u'清理固定资产',
                                       'order_id': Asset.id,
                                       'change_vourch': chang_account.id
                                       })
        return other_money_order

    @api.one
    # 按费用生成支出单
    # 借：费用（固定资产处置）
    # 贷：银行/现金
    def _clean_cost_generate_other_pay(self, Asset):
        pay_category = self.env.ref('asset.asset_clean_pay')  #
        if self.cost_bank and self.cost_bank.account_id.currency_id:
            raise UserError(u'系统占不支持外币结算固定资产')
        other_money_order = self.with_context(type='other_pay', modify_from_webclient=True).env['other.money.order'].create({
            'state': 'draft',
            'partner_id': None,
            'date': self.date,
            'bank_id': self.cost_bank.id,
        })
        other_money_order_line = self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id,
            'amount': self.clean_cost,
            'category_id': pay_category and pay_category.id
        })
        #other_money_order_line.onchange_category_id()
        other_money_order.other_money_done()
        self.env['chang.line'].create({'date': self.date,
                                       'period_id': self.period_id.id,
                                       'chang_name': u'清理固定资产',
                                       'order_id': Asset.id,
                                       'chang_other_money': other_money_order.id
                                       })
        return other_money_order

    @api.one
    # 按收入生成处置收入单
    # 借：银行/现金
    # 贷：收入（固定资产处置）
    def _clean_income_other_get(self, Asset):
        get_category = self.env.ref('asset.asset_clean_get')  #
        if self.income_bank and self.income_bank.account_id.currency_id:
            raise UserError(u'系统占不支持外币结算固定资产')
        other_money_order = self.with_context(type='other_get', modify_from_webclient=True).env['other.money.order'].create({
            'state': 'draft',
            'partner_id': None,
            'date': self.date,
            'bank_id': self.income_bank.id,
        })
        other_money_order_line = self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id,
            'amount': self.residual_income,
            'category_id': get_category and get_category.id
        })
        # other_money_order_line.onchange_category_id()
        other_money_order.other_money_done()
        # 找到结算单对应的凭证行并修改科目
        self.env['chang.line'].create({'date': self.date,
                                       'period_id': self.period_id.id,
                                       'chang_name': u'清理固定资产',
                                       'order_id': Asset.id,
                                       'change_other_many': other_money_order.id
                                       })
        return other_money_order

    @api.one
    # 按收入生成凭证
    # 借：科目
    # 贷：固定资产处置
    def _clean_income_voucher(self, Asset, clear_account_id):
        vouch_obj = self.env['voucher'].create({'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        # 借方行
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'处置固定资产',
                                         'debit': self.residual_income, 'account_id': self.income_account.id,
                                         })
        # 贷方行
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'处置固定资产',
                                         'credit': self.residual_income, 'account_id': clear_account_id.id,
                                         })
        vouch_obj.voucher_done()
        self.env['chang.line'].create({'date': self.date,
                                       'period_id': self.period_id.id,
                                       'chang_name': u'清理固定资产',
                                       'order_id': Asset.id,
                                       'change_vourch': vouch_obj.id
                                       })
        return vouch_obj

    @api.one
    # 按费用生成凭证
    # 借：固定资产处置
    # 贷：科目
    def _clean_cost_generate_voucher(self, Asset, clear_account_id):
        vouch_obj = self.env['voucher'].create({'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        # 借方行
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'处置固定资产',
                                         'debit': self.clean_cost, 'account_id': clear_account_id.id,
                                         })
        # 贷方行
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'处置固定资产',
                                         'credit': self.clean_cost, 'account_id': self.cost_account.id,
                                         })
        vouch_obj.voucher_done()
        self.env['chang.line'].create({'date': self.date,
                                       'period_id': self.period_id.id,
                                       'chang_name': u'清理固定资产',
                                       'order_id': Asset.id,
                                       'change_vourch': vouch_obj.id
                                       })
        return vouch_obj

    @api.one
    # 直接生成凭证
    # 借：累计折旧
    # 借：处置科目/其他科目
    # 贷：固定资产
    def _generate_voucher(self, Asset, income, depreciation, account_id):
        ''' 生成凭证，并确认 '''
        vouch_obj = self.env['voucher'].create({'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        Asset.write({'voucher_id': vouch_obj.id})
        if self.clean_type == 'guazhang':
            voucher_name = u'盘亏固定资产'
        else:
            voucher_name = u'处置固定资产'
        # 借方行,挂帐不存在income<0
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': voucher_name,
                                         'debit': income, 'account_id': account_id.id,
                                         })
        if depreciation:
            self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': voucher_name,
                                             'debit': depreciation,
                                             'account_id': Asset.account_accumulated_depreciation.id,
                                             })
        # 贷方行
        self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': voucher_name,
                                         'credit': Asset.cost, 'account_id': Asset.account_asset.id,
                                         })

        vouch_obj.voucher_done()
        self.env['chang.line'].create({'date': self.date,
                                       'period_id': self.period_id.id,
                                       'chang_name': voucher_name,
                                       'order_id': Asset.id,
                                       'change_vourch': vouch_obj.id
                                       })

        return vouch_obj

    @api.one
    # 挂帐直接生成凭证
    # 借：其他收入 OR  固定资产处置
    # 贷：固定资产处置   or  其他支出
    def _generate_handle_voucher(self, Asset, income, clear_account_id):
        ''' 生成凭证，并确认 '''
        if income == 0:
            pass
        vouch_obj = self.env['voucher'].create({'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        Asset.write({'voucher_id': vouch_obj.id})
        # 借方行,挂帐不存在income<0
        if income < 0:
            # 借方行
            self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'处置固定资产',
                                             'debit': -income, 'account_id': Asset.category_id.clean_costs.id,
                                             })
            # 贷方行
            self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'处置固定资产',
                                             'credit': -income, 'account_id': clear_account_id.id,
                                             })
        if income > 0:
            # 借方行
            self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'处置固定资产',
                                             'debit': income, 'account_id': clear_account_id.id,
                                             })
            # 贷方行
            self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'处置固定资产',
                                             'credit': income, 'account_id': Asset.category_id.clean_income.id,
                                             })
        vouch_obj.voucher_done()
        self.env['chang.line'].create({'date': self.date,
                                       'period_id': self.period_id.id,
                                       'chang_name': u'清理固定资产',
                                       'order_id': Asset.id,
                                       'change_vourch': vouch_obj.id
                                       })
        return vouch_obj

    @api.one
    # 处置固定资产
    def create_clean_account(self):
        if not self.env.context.get('active_id'):
            return
        Asset = self.env['asset'].browse(self.env.context.get('active_id'))
        clear_account_id = Asset.category_id.clear_account_id
        if self.clean_type == 'handle' and not (Asset.category_id.clean_income.id or Asset.category_id.clean_costs.id):
            raise UserError(u'处置固定资产必须要在固定资产分类中设置固定资产处置收入科目和固定资产处置成本科目。')
        if not Asset.account_accumulated_depreciation and not Asset.forever_no_depreciation:
            raise UserError(
                u'处置固定资产必须要在固定资产分类（%s）中设置固定资产处置收入科目和固定资产处置成本科目' % Asset.account_accumulated_depreciation.name)
        if self.clean_type == 'guazhang' and not self.clean_account.id:
            raise UserError(u'盘亏处理必须要挂账科目')
        depreciation2 = sum(line.cost_depreciation for line in Asset.line_ids)
        depreciation = Asset.depreciation_previous + depreciation2
        residual = Asset.cost - depreciation  # 残值=原值-累计折旧
        income = self.residual_income - self.clean_cost - residual  # 收入/支出=收入-支出-残值 大于0则为收入，小于0为支出
        Asset.no_depreciation = 1

        # 挂帐（盘亏）处理直接生成凭证
        if self.clean_type == 'guazhang':
            code = self.clean_account.code
            if code[:4] in error_code:
                raise UserError(u'您选择的类型和科目不匹配，请重新选择。')
            self._generate_voucher(Asset, residual, depreciation, self.clean_account)
            Asset.state = 'deficit'
        # 按发票收入生成收入单
        else:
            if not clear_account_id:
                raise UserError(u'请到固定分类处置科目维护')
            # 先处置到处置科目
            self._generate_voucher(Asset, residual, depreciation, clear_account_id)
            # 直接处理：费用>0且为生成其他付款单（流水）
            if self.clean_cost > 0 and self.cost_bank:
                self._clean_cost_generate_other_pay(Asset)
            # 直接处理：费用>0且为生成凭证
            if self.clean_cost > 0 and self.cost_account:
                code = self.cost_account.code
                if code[:4] in error_code:
                    raise UserError(u'您选择的类型和科目不匹配，请重新选择。')
                self._clean_cost_generate_voucher(Asset, clear_account_id)
            # 直接处理：收入>0且为生成其他收款单（流水）
            if self.residual_income > 0 and self.income_bank:
                self._clean_income_other_get(Asset)
            # 直接处理：收入>0且为生成凭证
            if self.residual_income > 0 and self.income_account:
                code = self.income_account.code
                if code[:4] in error_code:
                    raise UserError(u'您选择的类型和科目不匹配，请重新选择。')
                self._clean_income_voucher(Asset, clear_account_id)
            # 生成处置收入/支出凭证
            self._generate_handle_voucher(Asset, income, clear_account_id)
            Asset.state = 'clean'


class CreateChangWizard(models.TransientModel):
    '''固定资产变更'''
    _name = 'create.chang.wizard'
    _description = u'固定资产变更向导'

    SELECT = [('bank', u'现金/银行'),
              ('account', '科目')]

    @api.one
    @api.depends('chang_date')
    def _compute_period_id(self):
        ''' 根据变更日期取会计期间 '''
        self.period_id = self.env['finance.period'].get_period(self.chang_date)

    # 字段
    chang_date = fields.Date(u'变更日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    chang_cost = fields.Float(u'增加金额',
                              digits=dp.get_precision('Amount'))
    chang_depreciation_number = fields.Integer(u'变更折旧期间')
    chang_tax = fields.Float(
        u'增加税额', digits=dp.get_precision('Amount'))
    #chang_partner_id = fields.Many2one('partner', u'供应商', ondelete='restrict')
    asset_account_id = fields.Many2one(
        'finance.account', u'固定资产科目', )
    change_reason = fields.Text(u'变更原因')
    chang_type = fields.Selection(SELECT, u'类型',
                                   required=True,
                                   default='bank')
    account_credit = fields.Many2one(
        'finance.account', u'资产贷方科目', domain="[('account_type','=','normal')]")
    bank_account = fields.Many2one('bank.account', u'结算账户', ondelete='restrict',
                                   help=u'固定资产入账时：如现金，此处为选账户')
    account_ids = fields.Char(u'可使用贷方科目id', help=u'技术字段，用于过滤')

    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.model
    def default_get(self, fields):
        ''' 取默认值科目'''
        res = super(CreateChangWizard, self).default_get(fields)
        Asset = self.env['asset'].browse(self.env.context.get('active_id'))
        res.update({'asset_account_id':Asset.account_asset.id})
        return res

    @api.one
    def create_chang_account(self):
        ''' 创建变更对应的结算单，确认应付 '''
        ''' TODO 逻辑似乎不太对，原值和折旧期的变更都会引起每月折旧的金额变化，但是已经提过的折旧差异没有处理 
           xuan 说：以前的一定不能改'''
        if not self.env.context.get('active_id'):
            return
        Asset = self.env['asset'].browse(self.env.context.get('active_id'))
        chang_before_cost = Asset.cost
        chang_before_depreciation_number = Asset.depreciation_number
        Asset.cost = self.chang_cost + Asset.cost  # 历史成本
        Asset.surplus_value = Asset.cost - Asset.depreciation_previous  # 入账价值
        Asset.tax = Asset.tax + self.chang_tax  # 税
        Asset.depreciation_number = Asset.depreciation_number + \
                                    self.chang_depreciation_number  # 折旧期数
        Asset.depreciation_value = Asset.depreciation_value + Asset.category_id.depreciation_value * \
                                                              self.chang_cost / 100  # 残值
        Asset._get_cost_depreciation() # 运行折旧额计算
        if self.chang_cost > 0 and self.chang_type == 'bank':
            self._bank_account_change_other_pay(Asset, chang_before_cost, chang_before_depreciation_number)
        elif self.chang_cost > 0 and self.chang_type == 'account':
            self._construction_change_voucher(Asset, chang_before_cost, chang_before_depreciation_number)
        return True


    @api.one
    def _bank_account_change_other_pay(self, Asset, chang_before_cost, chang_before_depreciation_number):
        ''' 现金和银行支付的方式，选择结算账户，生成其他支出单 '''
        category = Asset.category_id.asset_other_money_pay_category  # 固定资产采购
        if not category:
            raise UserError(u'请在固定资产中设置固定资产的类别')

        other_money_order = Asset.with_context(type='other_pay', modify_from_webclient=True).env['other.money.order'].create({
            'state': 'draft',
            'date': self.chang_date ,
            'bank_id': self.bank_account.id,
        })
        Asset.write({'other_money_order': other_money_order.id})
        other_money_order_line = Asset.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id,
            'amount': self.chang_cost,
            'tax_rate': self.chang_cost and self.chang_tax / self.chang_cost * 100 or 0,
            'tax_amount': self.chang_tax,
            'category_id': category and category.id
        })
        # other_money_order_line.onchange_category_id()
        other_money_order.other_money_done()

        voucher_chang_account = self.env['voucher.line'].search(
            [('voucher_id', '=', other_money_order.voucher_id.id),
             ('account_id', '=', category.account_id.id)])
        voucher_chang_account.write({'account_id': Asset.account_asset.id})

        # 记录变更历史 - 原值变更
        self.env['chang.line'].create({'date': self.chang_date, 'period_id': self.period_id.id,
                                       'chang_before': chang_before_cost,
                                       'change_reason': self.change_reason,
                                       'chang_after': Asset.cost, 'chang_name': u'原值变更',
                                       'order_id': Asset.id, 'chang_other_money ':other_money_order.id
                                       })

        if self.chang_depreciation_number:
            self.env['chang.line'].create({'date': self.chang_date, 'period_id': self.period_id.id,
                                           'chang_before': chang_before_depreciation_number,
                                           'change_reason': self.change_reason,
                                           'chang_after': Asset.depreciation_number, 'chang_name': u'折旧期间变更',
                                           'order_id': Asset.id, 'chang_other_money ':other_money_order.id
                                           })

        return other_money_order

    @api.one
    def _construction_change_voucher(self, Asset, chang_before_cost, chang_before_depreciation_number):
        ''' 贷方科目选择在建工程，直接生成凭证 '''
        vals = {}
        vouch_obj = self.env['voucher'].create({'date': self.chang_date, 'ref': '%s,%s' % (Asset._name, Asset.id)})
        Asset.write({'voucher_id': vouch_obj.id})
        vals.update({'vouch_obj_id': vouch_obj.id, 'string': Asset.name, 'name': u'固定资产',
                     'amount': self.chang_cost + self.chang_tax, 'credit_account_id': self.account_credit.id,
                     'debit_account_id': Asset.account_asset.id,
                     'buy_tax_amount': self.chang_tax or 0
                     })
        self.env['money.invoice'].create_voucher_line(vals)
        vouch_obj.voucher_done()

        # 记录变更历史 - 原值变更
        self.env['chang.line'].create({'date': self.chang_date, 'period_id': self.period_id.id,
                                       'chang_before': chang_before_cost,
                                       'change_reason': self.change_reason,
                                       'chang_after': Asset.cost, 'chang_name': u'原值变更',
                                       'order_id': Asset.id, 'change_vourch': vouch_obj.id
                                       })

        if self.chang_depreciation_number:
            self.env['chang.line'].create({'date': self.chang_date, 'period_id': self.period_id.id,
                                           'chang_before': chang_before_depreciation_number,
                                           'change_reason': self.change_reason,
                                           'chang_after': Asset.depreciation_number, 'chang_name': u'折旧期间变更',
                                           'order_id': Asset.id, 'change_vourch': vouch_obj.id
                                           })

        return vouch_obj


class CreateAssetWizard(models.TransientModel):
    '''固定资产确认'''
    _name = 'create.asset.wizard'
    _description = u'固定资产处置向导'

    '''
    SELECT = [('partner', u'应付管理'),
               ('bank', u'现金/银行'),
              ('account','科目')]
    '''
    SELECT = [('bank', u'现金/银行'),
              ('account', '科目')]

    # 字段
    create_type = fields.Selection(SELECT, u'类型',
                                   required=True,
                                   default='bank')
    account_credit = fields.Many2one(
        'finance.account', u'资产贷方科目',
        help=u'固定资产入账时：如自建，此处为在建工程', domain="[('account_type','=','normal')]")
    partner_id = fields.Many2one('partner', u'供应商', ondelete='restrict',
                                 domain="[('s_category_id', '!=', False)]",
                                 help=u'固定资产入账时：如应付，此处为选供应商')
    bank_account = fields.Many2one('bank.account', u'结算账户', ondelete='restrict',
                                   help=u'固定资产入账时：如现金，此处为选账户')

    account_ids = fields.Char(u'可使用贷方科目id', help=u'技术字段，用于过滤')

    @api.model
    def default_get(self, fields):
        ''' 取默认值科目'''
        res = super(CreateAssetWizard, self).default_get(fields)
        account_ids = []
        for account in self.env['asset.account'].search([]):
            account_ids.append(account.name.id)
        res.update({'account_ids': account_ids})
        return res

    @api.one
    def _wrong_asset_done(self, Asset):
        ''' 固定资产确认入账前的验证 '''
        # todo 外币购固定资产
        if Asset.state == 'done':
            raise UserError(u'请不要重复确认！')
        if Asset.period_id.is_closed:
            raise UserError(u'该会计期间(%s)已结账！不能确认' % Asset.period_id.name)
        if Asset.cost <= 0:
            raise UserError(u'金额必须大于0！\n金额:%s' % Asset.cost)
        if Asset.tax < 0:
            raise UserError(u'税额必须大于0！\n税额:%s' % Asset.tax)
        if Asset.depreciation_previous < 0:
            raise UserError(u'以前折旧必须大于0！\n折旧金额:%s' %
                            Asset.depreciation_previous)
        if self.partner_id and self.partner_id.s_category_id.account_id.currency_id:
            raise UserError(u'系统占不支持外币结算固定资产')
        if self.bank_account and self.bank_account.account_id.currency_id:
            raise UserError(u'系统占不支持外币结算固定资产')
        if self.account_credit and self.account_credit.currency_id:
            raise UserError(u'系统占不支持外币结算固定资产')
        if self.create_type == 'account' and self.account_credit:
            code = self.account_credit.code
            if code[:4] in error_code:
                raise UserError(u'您选择的类型和科目不匹配，请重新选择。')

    @api.one
    def _partner_generate_invoice(self, Asset):
        ''' 赊购的方式，选择往来单位时，生成结算单'''
        categ = self.env.ref('asset.asset_expense')  # 固定资产采购
        # 创建结算单
        money_invoice = self.env['money.invoice'].create({
            'name': u'固定资产' + Asset.code,
            'partner_id': self.partner_id.id,
            'category_id': categ and categ.id,
            'date': Asset.date,
            'amount': Asset.amount,
            'reconciled': 0,
            'to_reconcile': Asset.amount,
            'date_due': fields.Date.context_today(Asset),
            'state': 'draft',
            'tax_amount': Asset.tax
        })
        Asset.write({'money_invoice': money_invoice.id})

        ''' 因分类上只能设置一个固定资产科目，这里要用当前固定资产的对应科目替换凭证 '''

        # 如未自动确认，则确认一下结算单
        if money_invoice.state != 'done':
            money_invoice.money_invoice_done()
        # 找到结算单对应的凭证行并修改科目
        chang_account = self.env['voucher.line'].search(
            [('voucher_id', '=', money_invoice.voucher_id.id),
             ('account_id', '=', categ.account_id.id)])
        chang_account.write({'account_id': Asset.account_asset.id})

        return money_invoice

    @api.one
    def _bank_account_generate_other_pay(self, Asset):
        ''' 现金和银行支付的方式，选择结算账户，生成其他支出单 '''
        category = Asset.category_id.asset_other_money_pay_category  # 固定资产采购
        if not category:
            raise UserError(u'请在固定资产中设置固定资产的类别')

        other_money_order = Asset.with_context(type='other_pay', modify_from_webclient=True).env['other.money.order'].create({
            'state': 'draft',
            'date': Asset.date,
            'bank_id': self.bank_account.id,
        })
        Asset.write({'other_money_order': other_money_order.id})
        other_money_order_line = Asset.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id,
            'amount': Asset.cost,
            'tax_rate': Asset.cost and Asset.tax / Asset.cost * 100 or 0,
            'tax_amount': Asset.tax,
            'category_id': category and category.id
        })
        # other_money_order_line.onchange_category_id()
        other_money_order.other_money_done()

        chang_account = self.env['voucher.line'].search(
            [('voucher_id', '=', other_money_order.voucher_id.id),
             ('account_id', '=', category.account_id.id)])
        chang_account.write({'account_id': Asset.account_asset.id})
        return other_money_order

    @api.one
    def _construction_generate_voucher(self, Asset):
        ''' 贷方科目选择在建工程，直接生成凭证 '''
        vals = {}
        vouch_obj = self.env['voucher'].create({'date': Asset.date, 'ref': '%s,%s' % (Asset._name, Asset.id)})
        Asset.write({'voucher_id': vouch_obj.id})
        vals.update({'vouch_obj_id': vouch_obj.id, 'string': Asset.name, 'name': u'固定资产',
                     'amount': Asset.amount, 'credit_account_id': self.account_credit.id,
                     'debit_account_id': Asset.account_asset.id,
                     'buy_tax_amount': Asset.tax or 0
                     })
        self.env['money.invoice'].create_voucher_line(vals)
        vouch_obj.voucher_done()

        return vouch_obj

    @api.one
    def create_asset(self):
        # 确认固定资产
        Asset = self.env['asset'].browse(self.env.context.get('active_id'))
        # 报错
        self._wrong_asset_done(Asset)
        # 非初始化固定资产生成入账凭证
        Asset.state = 'done'
        if not Asset.is_init:
            if self.create_type == 'partner' and self.partner_id:
                # 赊购
                self._partner_generate_invoice(Asset)
            if self.create_type == 'bank' and self.bank_account:
                # 现金购入
                self._bank_account_generate_other_pay(Asset)
            if self.create_type == 'account' and self.account_credit:
                # 在建工程转入
                self._construction_generate_voucher(Asset)
        return True


class AssetLine(models.Model):
    _name = 'asset.line'
    _description = u'资产折旧明细'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        ''' 根据记账日期取会计期间 '''
        self.period_id = self.env['finance.period'].get_period(self.date)

    order_id = fields.Many2one('asset', u'资产', index=True,
                               required=True, ondelete='restrict')
    cost_depreciation = fields.Float(
        u'折旧额', required=True, digits=dp.get_precision('Amount'))
    no_depreciation = fields.Float(u'未提折旧额')
    code = fields.Char(u'编码')
    name = fields.Char(u'名称')
    date = fields.Date(u'记账日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    voucher_number = fields.Char(u'凭证ID')


class CreateDepreciationWizard(models.TransientModel):
    """生成每月折旧的向导 根据输入的期间"""
    _name = "create.depreciation.wizard"
    _description = u'资产折旧向导'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        '''根据输入的日期取期间'''
        self.period_id = self.env['finance.period'].get_period(self.date)

    @api.model
    def _get_last_date(self):
        period_obj = self.env['finance.period']
        period_now = period_obj.get_date_now_period_id()
        if period_now:
            return period_obj.get_period_month_date_range(period_now)[1]
        else:
            return fields.Date.context_today(self)

    date = fields.Date(u'记账日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def _get_voucher_line(self, Asset, cost_depreciation, vouch_obj):
        ''' 借：累计折旧 '''
        res = {}
        if Asset.account_depreciation.id not in res:
            res[Asset.account_depreciation.id] = {'debit': 0}
        val = res[Asset.account_depreciation.id]
        val.update({'debit': val.get('debit') + cost_depreciation,
                    'voucher_id': vouch_obj.id,
                    'account_id': Asset.account_depreciation.id,
                    'name': u'固定资产折旧',
                    })

        ''' 贷：费用科目 '''
        if Asset.account_accumulated_depreciation.id not in res:
            res[Asset.account_accumulated_depreciation.id] = {'credit': 0}
            val = res[Asset.account_accumulated_depreciation.id]
            val.update({'credit': val.get('credit') + cost_depreciation,
                        'voucher_id': vouch_obj.id,
                        'account_id': Asset.account_accumulated_depreciation.id,
                        'name': u'固定资产折旧',
                        'ref': '%s,%s' % (self._name, self.id)
                        })
        return res

    @api.multi
    def _generate_asset_line(self, Asset, cost_depreciation, total):
        '''生成折旧明细行'''
        AssetLine = self.env['asset.line'].create({
            'date': self.date,
            'order_id': Asset.id,
            'period_id': self.period_id.id,
            'cost_depreciation': cost_depreciation,
            'name': Asset.name,
            'code': Asset.code,
            # 未提折旧：原值 - 已提折旧 - 本期折旧
            'no_depreciation': Asset.surplus_value - total - cost_depreciation,
        })
        return AssetLine

    @api.multi
    def create_depreciation(self):
        ''' 资产折旧，生成凭证和折旧明细'''

        vouch_obj = self.env['voucher'].create({'date': self.date})
        res = []
        asset_line_id_list = []
        for Asset in self.env['asset'].search([('no_depreciation', '=', False),  # 提折旧的
                                               ('state', '=', 'done'),  # 已确认
                                               ('period_id', '!=', self.period_id.id)]):  # 从入账下月开始
            # 本期折旧过，但折旧凭证被删除了
            for line in Asset.line_ids:
                if self.period_id == line.period_id and line.voucher_number :
                    generate_voucher_id = self.env['voucher'].search([('id','=',line.voucher_number)])
                    if not generate_voucher_id:
                        line.unlink()
            # 本期间没有折旧过，本期间晚于固定资产入账期间
            if self.period_id not in [line.period_id for line in Asset.line_ids] and \
                            self.env['finance.period'].period_compare(self.period_id, Asset.period_id) > 0:
                # 本月折旧
                cost_depreciation = Asset.cost_depreciation
                # 累计折旧
                total = sum(
                    line.cost_depreciation for line in Asset.line_ids) + Asset.depreciation_value
                # 最后一次折旧
                if Asset.surplus_value <= (total + cost_depreciation):
                    cost_depreciation = Asset.surplus_value - total
                    Asset.no_depreciation = 1
                # 构造凭证明细行字典
                res.append(self._get_voucher_line(
                    Asset, cost_depreciation, vouch_obj))

                # 生成折旧明细行
                asset_line_row = self._generate_asset_line(
                    Asset, cost_depreciation, total)
                asset_line_id_list.append(asset_line_row.id)
                    # 构造凭证明细行字典
        debit_line_dict, credit_line_dict = {}, {}
        for i in range(len(res)):
            for account_id, val in res[i].iteritems():
                # 生成借方凭证明细
                if 'debit' in val.keys():
                    if account_id not in debit_line_dict:
                        debit_line_dict[account_id] = val
                    else:
                        debit_line_dict[account_id]['debit'] += val['debit']
                # 生成贷方凭证明细
                if 'credit' in val.keys():
                    if account_id not in credit_line_dict:
                        credit_line_dict[account_id] = val
                    else:
                        credit_line_dict[account_id]['credit'] += val['credit']
        line_dict = dict(debit_line_dict.items() + credit_line_dict.items())
        for account_id, val in line_dict.iteritems():
            self.env['voucher.line'].create(dict(val, account_id=account_id))  # 创建凭证行

        # 没有凭证行则报错
        if not vouch_obj.line_ids:
            if not self._context.get('no_error'):
                raise UserError(u'本期没有需要折旧的固定资产。')
        for asset_line_id in asset_line_id_list:
            asset_line = self.env['asset.line'].search([('id','=',asset_line_id)], limit=1)
            asset_line.write({'voucher_number': vouch_obj.id})
        if vouch_obj.line_ids:
            vouch_obj.voucher_done()
        else:
            vouch_obj.unlink()

        # 界面转到本月折旧明细
        view = self.env.ref('asset.asset_line_tree')
        return {
            'view_mode': 'tree',
            'name': u'资产折旧明细行',
            'views': [(view.id, 'tree')],
            'res_model': 'asset.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', asset_line_id_list)]
        }


class ChangLine(models.Model):
    _name = 'chang.line'
    _description = u'资产变更明细'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        ''' 根据变更日期取会计期间 '''
        self.period_id = self.env['finance.period'].get_period(self.date)

    # 字段
    order_id = fields.Many2one('asset', u'订单编号', index=True,
                               required=True, ondelete='cascade')
    chang_name = fields.Char(u'变更内容', required=True)
    date = fields.Date(u'记账日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    chang_before = fields.Float(u'变更前')
    chang_after = fields.Float(u'变更后')
    chang_money_invoice = fields.Many2one(
        'money.invoice', u'对应结算单', readonly=True, ondelete='restrict')
    partner_id = fields.Many2one('partner', u'供应商')
    change_reason = fields.Text(u'变更原因')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    change_vourch = fields.Many2one(
        'voucher', u'会计凭证', readonly=True, ondelete='restrict')
    chang_other_money = fields.Many2one(
        'other.money.order', u'对应收支单', readonly=True, ondelete='restrict')


class Voucher(models.Model):
    ''' 在凭证上增加 引入固定资产 按钮逻辑 '''
    _inherit = 'voucher'

    @api.one
    def init_asset(self):
        '''删除以前引入的固定资产内容'''
        for line in self.line_ids:
            if line.init_obj == 'asset':
                line.unlink()

        '''引入固定资产初始化单据'''
        res = {}
        if self.env['asset'].search([('is_init', '=', True),
                                     ('state', '=', 'draft')]):
            raise UserError(u'有未确认的初始化固定资产')
        for Asset in self.env['asset'].search([('is_init', '=', True),
                                               ('state', '=', 'done')]):
            cost = Asset.cost
            if not Asset.category_id.is_depreciation:
                depreciation_previous = Asset.depreciation_previous
            '''固定资产'''
            if Asset.account_asset.id not in res:
                res[Asset.account_asset.id] = {'credit': 0, 'debit': 0}

            val = res[Asset.account_asset.id]
            val.update({'debit': val.get('debit') + cost,
                        'account_id': Asset.account_asset.id,
                        'voucher_id': self.id,
                        'init_obj': 'asset',
                        'name': '固定资产 期初'
                        })
            '''累计折旧'''
            if Asset.account_accumulated_depreciation and Asset.account_accumulated_depreciation.id not in res:
                res[Asset.account_accumulated_depreciation.id] = {
                    'credit': 0, 'debit': 0}
            if Asset.account_accumulated_depreciation:
                val = res[Asset.account_accumulated_depreciation.id]
                val.update({'credit': val.get('credit') + depreciation_previous,
                            'account_id': Asset.account_accumulated_depreciation.id,
                            'voucher_id': self.id,
                            'init_obj': 'asset',
                            'name': '固定资产 期初'
                            })

        for account_id, val in res.iteritems():
            if val.get('credit') == val.get('debit') == 0:
                continue
            self.env['voucher.line'].create(dict(val, account_id=account_id),
                                            )


class AssetAccount(models.Model):
    '''固定资产科目维护'''
    _name = 'asset.account'
    _description = u'固定资产监控科目'

    name = fields.Many2one(
        'finance.account', u'固定资产货方科目维护')
