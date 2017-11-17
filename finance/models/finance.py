# -*- coding: utf-8 -*-
import calendar
from datetime import datetime
import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

BALANCE_DIRECTIONS_TYPE = [
    ('in', u'借'),
    ('out', u'贷')]

MONTH_SELECTION = [
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

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
}


class Voucher(models.Model):
    '''新建凭证'''
    _name = 'voucher'
    _inherit = ['mail.thread']
    _order = 'period_id, name desc'
    _description = u'会计凭证'

    @api.model
    def _default_voucher_date(self):
        return self._default_voucher_date_impl()

    @api.model
    def _default_voucher_date_impl(self):
        ''' 获得默认的凭证创建日期 '''
        voucher_setting = self.env['ir.values'].get_default(
            'finance.config.settings', 'default_voucher_date')
        now_date = fields.Date.context_today(self)
        if voucher_setting == 'last' and self.search([], limit=1):
            create_date = self.search([], limit=1).date
        else:
            create_date = now_date
        return create_date

    @api.model
    def _select_objects(self):
        records = self.env['business.data.table'].search([])
        models = self.env['ir.model'].search(
            [('model', 'in', [record.name for record in records])])
        return [(model.model, model.name) for model in models]

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    document_word_id = fields.Many2one(
        'document.word', u'凭证字', ondelete='restrict', required=True,
        default=lambda self: self.env.ref('finance.document_word_1'))
    date = fields.Date(u'凭证日期', required=True, default=_default_voucher_date,
                       states=READONLY_STATES,
                       track_visibility='always', help=u'本张凭证创建的时间', copy=False)
    name = fields.Char(u'凭证号', track_visibility='always', copy=False)
    att_count = fields.Integer(
        u'附单据', default=1, help=u'原始凭证的张数', states=READONLY_STATES)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True, help=u'本张凭证发生日期对应的，会计期间')
    line_ids = fields.One2many(
        'voucher.line', 'voucher_id', u'凭证明细', copy=True, states=READONLY_STATES,)
    amount_text = fields.Float(u'总计', compute='_compute_amount', store=True,
                               track_visibility='always', help=u'凭证金额')
    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已审核'),
                              ('cancel', u'已作废')], u'状态', default='draft',
                             index=True,
                             track_visibility='always', help=u'凭证所属状态!')
    is_checkout = fields.Boolean(u'结账凭证', help=u'是否是结账凭证')
    is_init = fields.Boolean(u'是否初始化凭证', help=u'是否是初始化凭证')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    ref = fields.Reference(string=u'前置单据',
                           selection='_select_objects')

    @api.one
    def voucher_done(self):
        """
        审核 凭证按钮 所调用的方法
        :return: 主要是把 凭证的 state改变
        """
        if self.state == 'done':
            raise UserError(u'凭证%s已经审核,请不要重复审核！' % self.name)
        if self.period_id.is_closed:
            raise UserError(u'该会计期间已结账！不能审核')
        if not self.line_ids:
            raise ValidationError(u'请输入凭证行')
        for line in self.line_ids:
            if line.debit + line.credit == 0:
                raise ValidationError(u'单行凭证行 %s 借和贷不能同时为0' % line.account_id.name)
            if line.debit * line.credit != 0:
                raise ValidationError(u'单行凭证行不能同时输入借和贷\n 摘要为%s的凭证行 借方为:%s 贷方为:%s' %
                                      (line.name, line.debit, line.credit))
        debit_sum = sum([line.debit for line in self.line_ids])
        credit_sum = sum([line.credit for line in self.line_ids])
        precision = self.env['decimal.precision'].precision_get('Amount')
        debit_sum = round(debit_sum, precision)
        credit_sum = round(credit_sum, precision)
        if debit_sum != credit_sum:
            raise ValidationError(u'借贷方不平，无法审核!\n 借方合计:%s 贷方合计:%s' %
                                  (debit_sum, credit_sum))

        self.state = 'done'
        if self.is_checkout:   # 月结凭证不做反转
            return True
        for line in self.line_ids:
            if line.account_id.costs_types == 'out' and line.credit:
                # 费用类科目只能在借方记账,比如银行利息收入
                line.debit = -line.credit
                line.credit = 0
            if line.account_id.costs_types == 'in' and line.debit:
                # 收入类科目只能在贷方记账,比如退款给客户的情况
                line.credit = -line.debit
                line.debit = 0

    @api.one
    def voucher_can_be_draft(self):
        if self.ref:
            raise UserError(u'不能反审核由其他单据生成的凭证！')
        self.voucher_draft()

    @api.one
    def voucher_draft(self):
        if self.state == 'draft':
            raise UserError(u'凭证%s已经反审核,请不要重复反审核！' % self.name)
        if self.period_id.is_closed:
            raise UserError(u'%s期 会计期间已结账！不能反审核' % self.period_id.name)

        self.state = 'draft'

    @api.one
    @api.depends('line_ids')
    def _compute_amount(self):
        # todo 实现明细行总金额
        self.amount_text = str(sum([line.debit for line in self.line_ids]))

    # 重载write 方法
    @api.multi
    def write(self, vals):
        for order in self:  # 还需要进一步优化
            if self.env.context.get('call_module', False) == "checkout_wizard":
                return super(Voucher, self).write(vals)
            if order.period_id.is_closed is True:
                raise UserError(u'%s期 会计期间已结账，凭证不能再修改！' % order.period_id.name)
            if len(vals) == 1 and vals.get('state', False):  # 审核or反审核
                return super(Voucher, self).write(vals)
            else:
                order = self.browse(order.id)
                if order.state == 'done':
                    raise UserError(u'凭证%s已审核！修改请先反审核！' % order.name)
            return super(Voucher, self).write(vals)


class VoucherLine(models.Model):
    '''凭证明细'''
    _name = 'voucher.line'
    _description = u'会计凭证明细'

    @api.model
    def _default_get(self, data):
        ''' 给明细行摘要、借方金额、贷方金额字段赋默认值 '''
        move_obj = self.env['voucher']
        total = 0.0
        context = self._context
        if context.get('line_ids'):
            for move_line_dict in move_obj.resolve_2many_commands('line_ids', context.get('line_ids')):
                data['name'] = data.get('name') or move_line_dict.get('name')
                total += move_line_dict.get('debit', 0.0) - \
                    move_line_dict.get('credit', 0.0)
            data['debit'] = total < 0 and -total or 0.0
            data['credit'] = total > 0 and total or 0.0
        return data

    @api.model
    def default_get(self, fields):
        ''' 创建记录时，根据字段的 default 值和该方法给字段的赋值 来给 记录上的字段赋默认值 '''
        fields_data = super(VoucherLine, self).default_get(fields)
        data = self._default_get(fields_data)
        for f in data.keys():  # 判断 data key是否在 fields 里，如果不在则删除该 key。程序员开发用
            if f not in fields:
                del data[f]
        return data

    voucher_id = fields.Many2one('voucher', u'对应凭证', ondelete='cascade')
    name = fields.Char(u'摘要', required=True, help=u'描述本条凭证行的缘由')
    account_id = fields.Many2one(
        'finance.account', u'会计科目',
        ondelete='restrict', required=True)

    debit = fields.Float(u'借方金额', digits=dp.get_precision('Amount'), help=u'每条凭证行中只能记录借方金额或者贷方金额中的一个，\
    一张凭证中所有的凭证行的借方余额，必须等于贷方余额。')
    credit = fields.Float(u'贷方金额', digits=dp.get_precision('Amount'), help=u'每条凭证行中只能记录借方金额或者贷方金额中的一个，\
    一张凭证中所有的凭证行的借方余额，必须等于贷方余额。')
    partner_id = fields.Many2one(
        'partner', u'往来单位', ondelete='restrict', help=u'凭证行的对应的往来单位')

    currency_amount = fields.Float(u'外币金额', digits=dp.get_precision('Amount'))
    currency_id = fields.Many2one('res.currency', u'外币币别', ondelete='restrict')
    rate_silent = fields.Float(u'汇率')
    period_id = fields.Many2one(
        related='voucher_id.period_id', relation='finance.period', string=u'凭证期间', store=True)
    goods_qty = fields.Float(u'数量',
                             digits=dp.get_precision('Quantity'))
    goods_id = fields.Many2one('goods', u'商品', ondelete='restrict')
    auxiliary_id = fields.Many2one(
        'auxiliary.financing', u'辅助核算', help=u'辅助核算是对账务处理的一种补充,即实现更广泛的账务处理,\
        以适应企业管理和决策的需要.辅助核算一般通过核算项目来实现', ondelete='restrict')
    date = fields.Date(compute='_compute_voucher_date',
                       store=True, string=u'凭证日期')
    state = fields.Selection([('draft', u'草稿'), ('done', u'已审核'),('cancel', u'已作废')], compute='_compute_voucher_state',
                             index=True,
                             store=True, string=u'状态')
    init_obj = fields.Char(u'初始化对象', help=u'描述本条凭证行由哪个单证生成而来')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

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
        self.currency_id = self.account_id.currency_id
        self.rate_silent = self.account_id.currency_id.rate
        res = {
            'domain': {
                'partner_id': [('name', '=', False)],
                'goods_id': [('name', '=', False)],
                'auxiliary_id': [('name', '=', False)]}}
        if not self.account_id or not self.account_id.auxiliary_financing:
            return res
        if self.account_id.auxiliary_financing == 'customer':
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
                raise UserError(u'不能删除已审核的凭证行\n 所属凭证%s  凭证行摘要%s'
                                % (active_voucher_line.voucher_id.name, active_voucher_line.name))
        return super(VoucherLine, self).unlink()

    @api.multi
    def view_document(self):
        self.ensure_one()
        return {
            'name': u'凭证',
            'view_mode': 'form',
            'res_model': 'voucher',
            'res_id': self.voucher_id.id,
            'type': 'ir.actions.act_window',
        }


class FinancePeriod(models.Model):
    '''会计期间'''
    _name = 'finance.period'
    _order = 'name desc'
    _description = u'会计期间'

    name = fields.Char(
        u'会计期间',
        compute='_compute_name', readonly=True, store=True)
    is_closed = fields.Boolean(u'已结账', help=u'这个字段用于标识期间是否已结账，已结账的期间不能生成会计凭证。')
    year = fields.Char(u'会计年度', required=True, help=u'会计期间对应的年份')
    month = fields.Selection(
        MONTH_SELECTION, string=u'会计月份', required=True, help=u'会计期间对应的月份')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.one
    @api.depends('year', 'month')
    def _compute_name(self):
        """
        根据填写的月份年份 设定期间的name值
        :return: None
        """
        if self.year and self.month:
            self.name = '%s%s' % (self.year, str(self.month).zfill(2))

    @api.multi
    def period_compare(self, period_id_one, period_id_two):
        """
        比较期间的大小
        :param period_id_one: 要比较的期间 1
        :param period_id_two:要比较的期间 2
        :return: 1 0 -1 分别代表 期间1 大于 等于 小于 期间2
        """
        period_one_str = "%s-%s" % (period_id_one.year,
                                    str(period_id_one.month).zfill(2))
        period_two_str = "%s-%s" % (period_id_two.year,
                                    str(period_id_two.month).zfill(2))
        if period_one_str > period_two_str:
            return 1
        elif period_one_str < period_two_str:
            return -1
        else:
            return 0

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

    @api.model
    def get_init_period(self):
        '''系统启用的期间'''
        start_date = self.env.ref('base.main_company').start_date
        period_id = self.search([
            ('year', '=', start_date[0:4]),
            ('month', '=', int(start_date[5:7]))
        ])
        return period_id

    @api.multi
    def get_date_now_period_id(self):
        """
        默认是当前会计期间
        :return: 当前会计期间的对象 如果不存在则返回 False
        """
        datetime_str = datetime.now().strftime("%Y-%m-%d")
        datetime_str_list = datetime_str.split('-')
        period_row = self.search(
            [('year', '=', datetime_str_list[0]), ('month', '=', str(int(datetime_str_list[1])))])
        return period_row and period_row[0]

    @api.multi
    def get_period_month_date_range(self, period_id):
        """
        取得 period_id 期间的第一天 和最后一天
        :param period_id: 要取得一个月 最后一天和第一天的期间
        :return: 返回一个月的第一天和最后一天 （'2016-01-01','2016-01-31'）
        """
        month_day_range = calendar.monthrange(
            int(period_id.year), int(period_id.month))
        return ("%s-%s-01" % (period_id.year, period_id.month.zfill(2)), "%s-%s-%s" % (period_id.year, period_id.month.zfill(2), str(month_day_range[1])))

    @api.multi
    def get_year_fist_period_id(self):
        """
            获取本年创建过的第一个会计期间
            :return: 当前会计期间的对象 如果不存在则返回 False
            """
        datetime_str = datetime.now().strftime("%Y-%m-%d")
        datetime_str_list = datetime_str.split('-')
        period_row = self.search(
            [('year', '=', datetime_str_list[0])])
        period_list = sorted(map(int, [period.month for period in period_row]))
        if not period_row[0]:
            raise UserError(u'日期%s所在会计期间不存在！' % datetime_str)
        fist_period = self.search(
            [('year', '=', datetime_str_list[0]), ('month', '=', period_list[0])], order='name')
        return fist_period

    @api.multi
    def get_period(self, date):
        """
        根据参数date 得出对应的期间
        :param date: 需要取得期间的时间
        :return: 对应的期间
        """
        if date:
            period_id = self.search([
                ('year', '=', date[0:4]),
                ('month', '=', int(date[5:7]))
            ])
            if period_id:
                if period_id.is_closed and self._context.get('module_name', False) != 'checkout_wizard':
                    raise UserError(u'会计期间%s已关闭' % period_id.name)
            else:
                raise UserError(u'%s 对应的会计期间不存在' % date)
            return period_id

    _sql_constraints = [
        ('period_uniq', 'unique (year,month)', u'会计期间不能重复'),
    ]


class DocumentWord(models.Model):
    '''凭证字'''
    _name = 'document.word'
    _description = u'凭证字'

    name = fields.Char(u'凭证字')
    print_title = fields.Char(u'打印标题', help=u'凭证在打印时的显示的标题')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())


class FinanceAccount(models.Model):
    '''科目'''
    _name = 'finance.account'
    _order = "code"
    _description = u'会计科目'

    @api.one
    def compute_balance(self):
        """
        计算会计科目的当前余额
        :return:
        """
        lines = self.env['voucher.line'].search(
            [('account_id', '=', self.id),
             ('voucher_id.state', '=', 'done')])
        self.balance = sum((line.debit - line.credit) for line in lines)

    name = fields.Char(u'名称', required="1")
    code = fields.Char(u'编码', required="1")
    balance_directions = fields.Selection(
        BALANCE_DIRECTIONS_TYPE, u'余额方向', required="1", help=u'根据科目的类型，判断余额方向是借方或者贷方！')
    auxiliary_financing = fields.Selection([('customer', u'客户'),
                                           ('supplier', u'供应商'),
                                           ('member', u'个人'),
                                           ('project', u'项目'),
                                           ('department', u'部门'),
                                           ('goods', u'存货'),
                                           ], u'辅助核算', help=u'辅助核算是对账务处理的一种补充,即实现更广泛的账务处理,\n\
                                            以适应企业管理和决策的需要.辅助核算一般通过核算项目来实现')
    costs_types = fields.Selection([
        ('assets', u'资产'),
        ('debt', u'负债'),
        ('equity', u'所有者权益'),
        ('in', u'收入类'),
        ('out', u'费用类'),
        ('cost', u'成本类'),
    ], u'类型', required="1")
    currency_id = fields.Many2one('res.currency', u'外币币别')
    exchange = fields.Boolean(u'是否期末调汇')
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    balance = fields.Float(u'当前余额',
                           compute='compute_balance',
                           store=True,
                           digits=dp.get_precision('Amount'),
                           help=u'科目的当前余额',
                           )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', u'科目名称必须唯一。'),
        ('code', 'unique(code)', u'科目代码必须唯一。'),
    ]

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        """
        在其他model中用到account时在页面显示 code name balance如：2202 应付账款 当前余额（更有利于会计记账）
        :return:
        """
        result = []
        for line in self:
            account_name = line.code + ' ' + line.name
            if line.env.context.get('show_balance'):
                account_name += ' ' + str(line.balance)
            result.append((line.id, account_name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        '''会计科目按名字和编号搜索'''
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name + '%'),
                      ('name', operator, name)]
        accounts = self.search(domain + args, limit=limit)
        return accounts.name_get()

    @api.multi
    def get_smallest_code_account(self):
        """
        取得最小的code对应的account对象
        :return: 最小的code 对应的对象
        """
        finance_account_row = self.search([], order='code')
        return finance_account_row and finance_account_row[0]

    @api.multi
    def get_max_code_account(self):
        """
        取得最大的code对应的account对象
        :return: 最大的code 对应的对象
        """
        finance_account_row = self.search([], order='code desc')
        return finance_account_row and finance_account_row[0]


class AuxiliaryFinancing(models.Model):
    '''辅助核算'''
    _name = 'auxiliary.financing'
    _description = u'辅助核算'

    code = fields.Char(u'编码')
    name = fields.Char(u'名称')
    type = fields.Selection([
        ('member', u'个人'),
        ('project', u'项目'),
        ('department', u'部门'),
    ], u'分类', default=lambda self: self.env.context.get('type'))
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    _sql_constraints = [
        ('name_uniq', 'unique(name)', u'辅助核算不能重名')
    ]


class ResCompany(models.Model):
    '''继承公司对象,添加字段'''
    _inherit = 'res.company'

    profit_account = fields.Many2one(
        'finance.account', u'本年利润科目', ondelete='restrict', help=u'本年利润科目,本年中盈利的科目,在结转时会用到。')
    remain_account = fields.Many2one(
        'finance.account', u'未分配利润科目', ondelete='restrict', help=u'未分配利润科目。')
    import_tax_account = fields.Many2one('finance.account', u"进项税科目", ondelete='restrict',
                                         help=u'进项税额，是指纳税人购进货物、加工修理修配劳务、服务、无形资产或者不动产，支付或者负担的增值税额。')
    output_tax_account = fields.Many2one(
        'finance.account', u"销项税科目", ondelete='restrict')

    operating_cost_account_id = fields.Many2one('finance.account', ondelete='restrict',
                                                string=u'生产费用科目', help=u'用在组装拆卸的费用上')


class BankAccount(models.Model):
    _inherit = 'bank.account'

    @api.one
    @api.depends('account_id')
    def _compute_currency_id(self):
        self.currency_id = self.account_id.currency_id.id

    account_id = fields.Many2one('finance.account', u'科目')
    currency_id = fields.Many2one(
        'res.currency', u'外币币别', compute='_compute_currency_id', store=True)
    currency_amount = fields.Float(u'外币金额', digits=dp.get_precision('Amount'))


class CoreCategory(models.Model):
    '''继承core cotegory，添加科目类型'''
    _inherit = 'core.category'

    account_id = fields.Many2one('finance.account', u'科目', help=u'科目')


class ChangeVoucherName(models.Model):
    ''' 修改凭证编号 '''
    _name = 'change.voucher.name'
    _description = u'月末凭证变更记录'

    period_id = fields.Many2one('finance.period', u'会计期间')
    before_voucher_name = fields.Char(u'以前凭证号')
    after_voucher_name = fields.Char(u'更新后凭证号')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())


class Dupont(models.Model):
    _name = 'dupont'
    _description = u'企业财务指标'
    _rec_name = 'period_id'
    _order = 'period_id'

    period_id = fields.Many2one('finance.period', u'期间', index=True)
    kpi = fields.Char(u'指标')
    val = fields.Float(u'值')

    @api.model
    def fill(self, period_id):

        if self.search([('period_id', '=', period_id.id)]):
            return True

        ta = te = income = ni = roe = roa = em = 0.0

        for b in self.env['trial.balance'].search([('period_id', '=', period_id.id)]):
            if b.subject_name_id.costs_types == 'assets':
                ta += b.ending_balance_debit - b.ending_balance_credit
            if b.subject_name_id.costs_types == 'equity':
                te += b.ending_balance_credit - b.ending_balance_debit
            if b.subject_name_id.costs_types == 'in':
                income += b.current_occurrence_credit
            if b.subject_name_id == self.env.user.company_id.profit_account:
                ni = b.current_occurrence_credit

        roe = te and ni / te * 100
        roa = ta and ni / ta * 100
        em = te and ta / te * 100
        res = {u'资产': ta, u'权益': te, u'收入': income, u'净利': ni,
               u'权益净利率': roe, u'资产净利率': roa, u'权益乘数': em}
        for k in res:
            self.create({'period_id': period_id.id, 'kpi': k, 'val': res[k]})
