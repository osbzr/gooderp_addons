# -*- coding: utf-8 -*-
import calendar
from datetime import datetime
import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

FIANNCE_CATEGORY_TYPE = [
    ('finance_account', u'会计科目'),
    ('auxiliary_financing', u'辅助核算')]

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


class voucher(models.Model):
    '''新建凭证'''
    _name = 'voucher'
    _inherit = ['mail.thread']
    _order = 'period_id , name desc'

    @api.model
    def _default_voucher_date(self):
        return self._default_voucher_date_impl()
    @api.model
    def _default_voucher_date_impl(self):
        ''' 获得默认的凭证创建日期 '''
        voucher_setting = self.env['ir.values'].get_default('finance.config.settings', 'default_voucher_date')
        now_date = fields.Date.context_today(self)
        if voucher_setting == 'last' and self.search([], limit=1):
            create_date = self.search([], limit=1).date
        else:
            create_date = now_date
        return create_date

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    document_word_id = fields.Many2one(
        'document.word', u'凭证字', ondelete='restrict', required=True,
        default=lambda self: self.env.ref('finance.document_word_1'), help=u'“收款凭证”，凭证字就是“收”\n“付款凭证”，凭证字就是“付”\
        “转帐凭证”，凭证字就是“转”\n“记款凭证”，凭证字就是“记” (可以不用以上三种凭证字，就用记字也可以)')
    date = fields.Date(u'凭证日期', required=True, default=_default_voucher_date,
                       track_visibility='always', help=u'本张凭证创建的时间！', copy=False)
    name = fields.Char(u'凭证号', track_visibility='always', copy=False)
    att_count = fields.Integer(u'附单据', default=1, help='原始凭证的张数！')
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True, help=u'本张凭证发生日期对应的，会计期间！')
    line_ids = fields.One2many('voucher.line', 'voucher_id', u'凭证明细', copy=True)
    amount_text = fields.Float(u'总计', compute='_compute_amount', store=True,
                               track_visibility='always',help=u'凭证金额')
    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已审核')], u'状态', default='draft',
                             track_visibility='always',help=u'凭证所属状态!')
    is_checkout = fields.Boolean(u'结账凭证',help=u'是否是结账凭证!')
    is_init = fields.Boolean(u'是否初始化凭证',help=u'是否是初始化凭证!')

    @api.one
    def voucher_done(self):
        """
        审核 凭证按钮 所调用的方法
        :return: 主要是把 凭证的 state改变
        """
        if self.state == 'done':
            raise UserError(u'请不要重复审核！')
        if self.period_id.is_closed:
            raise UserError(u'该会计期间已结账！不能审核')
        if not self.line_ids:
            raise ValidationError(u'请输入凭证行')
        for line in self.line_ids:
            if line.debit + line.credit == 0:
                raise ValidationError(u'单行凭证行借和贷不能同时为0\n 借方金额为: %s 贷方金额为:%s' % (line.debit, line.credit))
            if line.debit * line.credit != 0:
                raise ValidationError(u'单行凭证行不能同时输入借和贷\n 摘要为%s的凭证行 借方为:%s 贷方为:%s' %
                                      (line.name, line.debit, line.credit))
        debit_sum = sum([line.debit for line in self.line_ids])
        credit_sum = sum([line.credit for line in self.line_ids])
        precision = self.env['decimal.precision'].precision_get('Account')
        debit_sum = round(debit_sum, precision)
        credit_sum = round(credit_sum, precision)
        if debit_sum != credit_sum:
            raise ValidationError(u'借贷方不平!\n 借方合计:%s 贷方合计:%s' % (debit_sum, credit_sum))

        self.state = 'done'

    @api.one
    def voucher_draft(self):
        if self.state == 'draft':
            raise UserError(u'凭证%s已经审核,请不要重复反审核！' % self.name)
        if self.period_id.is_closed:
            raise UserError(u'%s期 会计期间已结账！不能反审核' % self.period_id.name)
        self.state = 'draft'

    @api.one
    @api.depends('line_ids')
    def _compute_amount(self):
        # todo 实现明细行总金额
        self.amount_text = str(sum([line.debit for line in self.line_ids]))

    @api.multi
    def unlink(self):
        for active_voucher in self:
            if active_voucher.state == 'done':
                raise UserError(u'凭证%s已审核,不能删除已审核的凭证'%active_voucher.name)
        return super(voucher, self).unlink()

    # 重载write 方法
    @api.multi
    def write(self, vals):
        if self.env.context.get('call_module', False) == "checkout_wizard":
            return super(voucher, self).write(vals)
        if self.period_id.is_closed is True:
            raise UserError(u'%s期 会计期间已结账，凭证不能再修改！'%self.period_id.name)
        if len(vals) == 1 and vals.get('state', False):  # 审核or反审核
            return super(voucher, self).write(vals)
        else:
            if self.state == 'done':
                raise UserError(u'凭证%s已审核！修改请先反审核！'%self.name)
        return super(voucher, self).write(vals)

class voucher_line(models.Model):
    '''凭证明细'''
    _name = 'voucher.line'

    @api.model
    def _default_get(self, fields):
        data = super(voucher_line, self).default_get(fields)
        move_obj = self.env['voucher']
        total = 0.0
        context= self._context
        if context.get('line_ids'):
            for move_line_dict in move_obj.resolve_2many_commands('line_ids', context.get('line_ids')):
                data['name'] = data.get('name') or move_line_dict.get('name')
                total += move_line_dict.get('debit', 0.0) - move_line_dict.get('credit', 0.0)
            data['debit'] = total < 0 and -total or 0.0
            data['credit'] = total > 0 and total or 0.0
        return data

    @api.model
    def default_get(self, fields):
        data = self._default_get(fields)
        for f in data.keys():
            if f not in fields:
                del data[f]
        return data

    voucher_id = fields.Many2one('voucher', u'对应凭证', ondelete='cascade')
    name = fields.Char(u'摘要', required=True, help='描述本条凭证行的缘由！')
    account_id = fields.Many2one(
        'finance.account', u'会计科目',
        ondelete='restrict', required=True)

    debit = fields.Float(u'借方金额', digits=dp.get_precision(u'金额'),help='每条凭证行中只能记录借方金额或者贷方金额中的一个，\
    一张凭证中所有的凭证行的借方余额，必须等于贷方余额！')
    credit = fields.Float(u'贷方金额', digits=dp.get_precision(u'金额'),help='每条凭证行中只能记录借方金额或者贷方金额中的一个，\
    一张凭证中所有的凭证行的借方余额，必须等于贷方余额！')
    partner_id = fields.Many2one('partner', u'往来单位', ondelete='restrict', help='凭证行的对应的往来单位')

    currency_amount = fields.Float(u'外币金额', digits=dp.get_precision(u'金额'))
    currency_id = fields.Many2one('res.currency', u'外币币别', ondelete='restrict')
    rate_silent = fields.Float(u'汇率')
    period_id = fields.Many2one(related='voucher_id.period_id', relation='finance.period', string='凭证期间', store=True)
    goods_id = fields.Many2one('goods', u'商品', ondelete='restrict')
    auxiliary_id = fields.Many2one(
        'auxiliary.financing', u'辅助核算',help='辅助核算是对账务处理的一种补充,即实现更广泛的账务处理,\
        以适应企业管理和决策的需要.辅助核算一般通过核算项目来实现',ondelete='restrict')
    date = fields.Date(compute='_compute_voucher_date', store=True, string=u'凭证日期')
    state = fields.Selection([('draft', u'草稿'),('done', u'已审核')], compute='_compute_voucher_state',
                             store=True, string=u'状态')
    init_obj = fields.Char(u'摘要', help='描述本条凭证行由哪个单证生成而来！')

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
        if not self.account_id or not self.account_id.auxiliary_financing:
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
                raise UserError(u'不能删除已审核的凭证行\n 所属凭证%s  凭证行摘要%s'
                                %(active_voucher_line.voucher_id.name,active_voucher_line.name))
        return super(voucher_line, self).unlink()


class finance_period(models.Model):
    '''会计期间'''
    _name = 'finance.period'
    _order = 'year desc,month desc '
    name = fields.Char(
        u'会计期间',
        compute='_compute_name', readonly=True, store=True)
    is_closed = fields.Boolean(u'已结账',help='这个字段用于标识期间是否已结账，已结账的期间不能生成会计凭证！')
    year = fields.Char(u'会计年度', required=True,help='会计期间对应的年份')
    month = fields.Selection(MONTH_SELECTION, string=u'会计月份', required=True,help='会计期间对应的月份')

    @api.one
    @api.depends('year', 'month')
    def _compute_name(self):
        """
        根据填写的月份年份 设定期间的name值
        :return: None
        """
        if self.year and self.month:
            self.name = u'%s年 第%s期' % (self.year, self.month)

    @api.multi
    def period_compare(self,period_id_one,period_id_two):
        """
        比较期间的大小
        :param period_id_one: 要比较的期间 1
        :param period_id_two:要比较的期间 2
        :return: 1 0 -1 分别代表 期间1 大于 等于 小于 期间2
        """
        period_one_str = "%s-%s"%(period_id_one.year,str(period_id_one.month).zfill(2))
        period_two_str = "%s-%s"%(period_id_two.year,str(period_id_two.month).zfill(2))
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
    @api.multi
    def get_date_now_period_id(self):
        """
        默认是当前会计期间
        :return: 当前会计期间的对象 如果不存在则返回 False
        """
        datetime_str = datetime.now().strftime("%Y-%m-%d")
        datetime_str_list = datetime_str.split('-')
        period_row = self.env['finance.period'].search(
            [('year', '=', datetime_str_list[0]), ('month', '=', str(int(datetime_str_list[1])))])
        return period_row and period_row[0]

    @api.multi
    def get_period_month_date_range(self, period_id):
        """
        取得 period_id 期间的第一天 和最后一天
        :param period_id: 要取得一个月 最后一天和第一天的期间
        :return: 返回一个月的第一天和最后一天 （'2016-01-01','2016-01-31'）
        """
        month_day_range = calendar.monthrange(int(period_id.year), int(period_id.month))
        return ("%s-%s-01" % (period_id.year, period_id.month), "%s-%s-%s" % (period_id.year, period_id.month, str(month_day_range[1])))

    @api.multi
    def get_year_fist_period_id(self):
        """
            获取本年创建过的第一个会计期间
            :return: 当前会计期间的对象 如果不存在则返回 False
            """
        datetime_str = datetime.now().strftime("%Y-%m-%d")
        datetime_str_list = datetime_str.split('-')
        period_row = self.env['finance.period'].search(
            [('year', '=', datetime_str_list[0])])
        period_list = sorted(map(int, [period.month for period in period_row]))
        if not period_row[0]:
            raise UserError(u'日期%s所在会计期间不存在！'%datetime_str)
        fist_period = self.search([('year', '=', datetime_str_list[0]), ('month', '=', period_list[0])], order='name')
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
                raise UserError(u'%s 对应的会计期间不存在'%date)
            return period_id

    _sql_constraints = [
        ('period_uniq', 'unique (year,month)', u'会计区间不能重复'),
    ]


class document_word(models.Model):
    '''凭证字'''
    _name = 'document.word'
    name = fields.Char(u'凭证字')
    print_title = fields.Char(u'打印标题',help='凭证在打印时的显示的标题')


class finance_account(models.Model):
    '''科目'''
    _name = 'finance.account'
    _order = "code"

    name = fields.Char(u'名称', required="1")
    code = fields.Char(u'编码', required="1")
    balance_directions = fields.Selection(BALANCE_DIRECTIONS_TYPE, u'余额方向', required="1", help=u'借方余额大于贷方余\
    额，则方向为借，反之则为贷！')
    auxiliary_financing = fields.Selection([('partner', u'客户'),
                                            ('supplier', u'供应商'),
                                            ('member', u'个人'),
                                            ('project', u'项目'),
                                            ('department', u'部门'),
                                            ('goods', u'存货'),
                                            ], u'辅助核算', help=u'辅助核算是对账务处理的一种补充,即实现更广泛的账务处理,\n\
                                            以适应企业管理和决策的需要.辅助核算一般通过核算项目来实现')
    costs_types = fields.Selection([
        ('assets', U'资产'),
        ('debt', U'负债'),
        ('equity', U'所有者权益'),
        ('in', u'收入类'),
        ('out', u'费用类')
    ], u'类型', required="1")
    currency_id = fields.Many2one('res.currency', u'外币币别')
    exchange = fields.Boolean(u'是否期末调汇')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', u'科目名称必须唯一!'),
        ('code', 'unique(code)', u'科目代码必须唯一!'),
    ]

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        """
        在其他model中用到account时在页面显示 code name 如：2202 应付账款 （更有利于会计记账）
        :return:
        """
        result = []
        for line in self:
            account_name = line.code + ' ' + line.name
            result.append((line.id, account_name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        '''会计科目按名字和编号搜索'''
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
        accounts = self.search(domain + args, limit=limit)
        return accounts.name_get()

    @api.multi
    def get_smallest_code_account(self):
        """
        取得最小的code对应的account对象
        :return: 最小的code 对应的对象
        """
        finance_account_row = self.search([],order='code')
        return finance_account_row and finance_account_row[0]


    @api.multi
    def get_max_code_account(self):
        """
        取得最大的code对应的account对象
        :return: 最大的code 对应的对象
        """
        finance_account_row = self.search([],order='code desc')
        return finance_account_row and finance_account_row[0]


class auxiliary_financing(models.Model):
    '''辅助核算'''
    _name = 'auxiliary.financing'

    code = fields.Char(u'编码')
    name = fields.Char(u'名称')
    type = fields.Selection([
        ('member', u'个人'),
        ('project', u'项目'),
        ('department', u'部门'),
    ], u'分类', default=lambda self: self.env.context.get('type'))

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '辅助核算不能重名')
    ]


class res_company(models.Model):
    '''继承公司对象,添加字段'''
    _inherit = 'res.company'

    profit_account = fields.Many2one('finance.account', u'本年利润科目', ondelete='restrict', help=u'本年利润科目,本年中盈利的科目！在结转时会用到!')
    remain_account = fields.Many2one('finance.account', u'未分配利润科目', ondelete='restrict', help=u'未分配利润科目！')
    import_tax_account = fields.Many2one('finance.account', u"进项税科目", ondelete='restrict', 
                                         help=u'进项税额，是指纳税人购进货物、加工修理修配劳务、服务、无形资产或者不动产，支付或者负担的增值税额。')
    output_tax_account = fields.Many2one('finance.account', u"销项税科目", ondelete='restrict')

    operating_cost_account_id = fields.Many2one('finance.account', ondelete='restrict',
                                                string=u'生产费用科目', help='用在组装拆卸的费用上')

class bank_account(models.Model):
    _inherit = 'bank.account'
    @api.one
    @api.depends('account_id')
    def _compute_currency_id(self):
        self.currency_id = self.account_id.currency_id.id

    account_id = fields.Many2one('finance.account', u'科目')
    currency_id = fields.Many2one('res.currency', u'外币币别', compute='_compute_currency_id', store=True, readonly=True)
    currency_amount = fields.Float(u'外币金额', digits=dp.get_precision(u'金额'), readonly=True)

class core_category(models.Model):
    _inherit = 'core.category'
    account_id = fields.Many2one('finance.account', u'科目', help=u'科目')

class chang_voucher_name(models.Model) :
    _name = 'chang.voucher.name'
    period_id = fields.Many2one('finance.period', u'会计期间')
    before_voucher_name = fields.Char(u'以前凭证号')
    after_voucher_name = fields.Char(u'更新后凭证号')
