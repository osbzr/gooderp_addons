# -*- coding: utf-8 -*-

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError
from datetime import datetime

FIANNCE_CATEGORY_TYPE = [
    ('finance_account', u'会计科目'),
    ('auxiliary_financing', u'辅助核算')]

BALANCE_DIRECTIONS_TYPE = [
    ('in', u'借'),
    ('out', u'贷')]

MOUTH_SELECTION = [
    ('1', u'01'),
    ('2', u'02'),
    ('3', u'03'),
    ('4', u'04'),
    ('5', u'05'),
    ('6', u'06'),
    ('7', u'07'),
    ('8', u'08'),
    ('9', u'09'),
    ('10', u'10'),
    ('11', u'11'),
    ('12', u'12')]


class voucher(models.Model):
    '''新建凭证'''
    _name = 'voucher'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    document_word_id = fields.Many2one(
        'document.word', u'凭证字', ondelete='restrict', required=True,
        default=lambda self: self.env.ref('finance.document_word_1'))
    date = fields.Date(
        u'凭证日期', required=True,
        default=datetime.now().strftime('%Y-%m-%d'))
    name = fields.Char(u'凭证号')
    att_count = fields.Integer(u'附单据', default=1)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    line_ids = fields.One2many('voucher.line', 'voucher_id', u'凭证明细')
    amount_text = fields.Char(u'总计', compute='_compute_amount', store=True)
    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已审核')], u'状态', default='draft')
    is_checkout = fields.Boolean(u'结账凭证')

    @api.one
    def voucher_done(self):
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        if self.period_id.is_closed == True:
            raise except_orm(u'错误', u'该会计期间已结账！不能审核')
        self.state = 'done'

    @api.one
    def voucher_draft(self):
        if self.state == 'draft':
            raise except_orm(u'错误', u'请不要重复反审核！')
        if self.period_id.is_closed == True:
            raise except_orm(u'错误', u'该会计期间已结账！不能反审核')
        self.state = 'draft'

    @api.one
    @api.depends('line_ids')
    def _compute_amount(self):
        # todo 实现明细行总金额
        self.amount_text = str(sum([line.debit for line in self.line_ids]))

    @api.one
    @api.constrains('line_ids')
    def _check_balance(self):
        debit_sum = sum([line.debit for line in self.line_ids])
        credit_sum = sum([line.credit for line in self.line_ids])
        if debit_sum != credit_sum:
            raise ValidationError(u'借贷方不平')

    @api.one
    @api.constrains('line_ids')
    def _check_line(self):
        if not self.line_ids:
            raise ValidationError(u'请输入凭证行')
        for line in self.line_ids:
            if line.debit + line.credit == 0:
                raise ValidationError(u'单行凭证行借和贷不能同时为0')
            if line.debit * line.credit != 0:
                raise ValidationError(u'单行凭证行不能同时输入借和贷')

    @api.multi
    def unlink(self):
        for active_voucher in self:
            if active_voucher.state == 'done':
                raise except_orm(u'错误', u'不能删除已审核的凭证')
        return super(voucher, self).unlink()


class voucher_line(models.Model):
    '''凭证明细'''
    _name = 'voucher.line'

    voucher_id = fields.Many2one('voucher', u'对应凭证', ondelete='cascade')
    name = fields.Char(u'摘要', required=True)
    account_id = fields.Many2one(
        'finance.account', u'会计科目',
        ondelete='restrict', required=True)
    debit = fields.Float(u'借方金额', digits_compute=dp.get_precision(u'金额'))
    credit = fields.Float(u'贷方金额', digits_compute=dp.get_precision(u'金额'))
    partner_id = fields.Many2one('partner', u'往来单位', ondelete='restrict')
    goods_id = fields.Many2one('goods', u'商品', ondelete='restrict')
    auxiliary_id = fields.Many2one(
        'auxiliary.financing', u'辅助核算',
        ondelete='restrict')
    date = fields.Date(compute='_compute_voucher_date', store=True, string='凭证日期')
    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已审核')], compute='_compute_voucher_state', store=True, string='状态')

    @api.one
    @api.depends('voucher_id.date')
    def _compute_voucher_date(self):
        # todo 实现明细行总金额
        self.date = self.voucher_id.date

    @api.one
    @api.depends('voucher_id.state')
    def _compute_voucher_state(self):
        # todo 实现明细行总金额
        self.state = self.voucher_id.state

    @api.multi
    @api.onchange('account_id')
    def onchange_account_id(self):
        res = {
            'domain': {
                'partner_id': [('name', '=', False)],
                'goods_id': [('name', '=', False)],
                'auxiliary_id': [('name', '=', False)]}}
        if not self.account_id:
            return res
        if not self.account_id.auxiliary_financing:
            return res
        if self.account_id.auxiliary_financing == 'partner':
            res['domain']['partner_id'] = [('c_category_id', '!=', False)]
        elif self.account_id.auxiliary_financing == 'supplier':
            res['domain']['partner_id'] = [('s_category_id', '!=', False)]
        elif self.account_id.auxiliary_financing == 'goods':
            res['domain']['goods_id'] = []
        else:
            res['domain']['auxiliary_id'] = [
                ('type', '=', self.account_id.auxiliary_financing)]
        return res

    @api.multi
    def unlink(self):
        for active_voucher_line in self:
            if active_voucher_line.voucher_id.state == 'done':
                raise except_orm(u'错误', u'不能删除已审核的凭证行')
        return super(voucher_line, self).unlink()


class finance_period(models.Model):
    '''会计期间'''
    _name = 'finance.period'

    name = fields.Char(
        u'会计期间',
        compute='_compute_name', readonly=True, store=True)
    is_closed = fields.Boolean(u'已结账')
    year = fields.Char(u'会计年度', required=True)
    month = fields.Selection(MOUTH_SELECTION, string=u'会计月份', required=True)

    @api.one
    @api.depends('year', 'month')
    def _compute_name(self):
        if self.year and self.month:
            self.name = u'%s年 第%s期' % (self.year, self.month)

    @api.model
    def init_period(self):
        ''' 根据系统启用日期（安装core模块的日期）创建 '''
        current_date = self.env.ref('base.main_company').start_date
        period_id = self.search([
            ('year', '=', current_date[0:4]),
            ('month', '=', int(current_date[5:7]))
        ])
        if not period_id:
            return self.create({'year': current_date[0:4],
                                'month': str(int(current_date[5:7])), })

    @api.multi
    def get_period(self, date):
        if date:
            period_id = self.search([
                ('year', '=', date[0:4]),
                ('month', '=', int(date[5:7]))
            ])
            if period_id:
                return period_id
            else:
                raise except_orm(u'错误', u'此日期对应的会计期间不存在')

    _sql_constraints = [
        ('period_uniq', 'unique (year,month)', u'会计区间不能重复'),
    ]


class document_word(models.Model):
    '''凭证字'''
    _name = 'document.word'
    name = fields.Char(u'凭证字')
    print_title = fields.Char(u'打印标题')


class finance_account(models.Model):
    '''科目'''
    _name = 'finance.account'
    name = fields.Char(u'名称')
    code = fields.Char(u'编码', required="1")
    balance_directions = fields.Selection(BALANCE_DIRECTIONS_TYPE, u'余额方向')
    auxiliary_financing = fields.Selection([('partner', u'客户'),
                                            ('supplier', u'供应商'),
                                            ('member', u'个人'),
                                            ('project', u'项目'),
                                            ('department', u'部门'),
                                            ('goods', u'存货'),
                                            ], u'辅助核算')
    costs_types = fields.Selection([
        ('assets', U'资产'),
        ('debt', U'负债'),
        ('equity', U'所有者权益'),
        ('in', u'收入类'),
        ('out', u'费用类')
    ], u'类型')
    state = fields.Boolean(u'状态')


class finance_category(models.Model):
    '''财务类别下拉选项'''
    _name = 'finance.category'
    name = fields.Char(u'名称')
    type = fields.Selection(FIANNCE_CATEGORY_TYPE, u'类型',
                            default=lambda self: self._context.get('type'))


class auxiliary_financing(models.Model):
    '''辅助核算'''
    _name = 'auxiliary.financing'

    code = fields.Char(u'编码')
    name = fields.Char(u'名称')
    type = fields.Selection([
        ('member', u'个人'),
        ('project', u'项目'),
        ('department', u'部门'),
    ], u'分类')


class res_company(models.Model):
    '''继承公司对象,添加字段'''
    _inherit = 'res.company'

    profit_account = fields.Many2one('finance.account', u'本年利润科目', ondelete='restrict')
    remain_account = fields.Many2one('finance.account', u'未分配利润科目', ondelete='restrict')


class bank_account(models.Model):
    _inherit = 'bank.account'
    account_id = fields.Many2one('finance.account', u'账户')


class core_category(models.Model):
    _inherit = 'core.category'
    account_id = fields.Many2one('finance.account', u'账户')
