# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class CheckoutWizard(models.TransientModel):
    '''月末结账的向导'''
    _name = 'checkout.wizard'
    _description = u'月末结账向导'

    @api.model
    def _get_last_date(self):
        period_obj = self.env['finance.period']
        period_now = period_obj.get_date_now_period_id()
        if period_now:
            return period_obj.get_period_month_date_range(period_now)[1]
        else:
            return fields.Date.context_today(self)

    period_id = fields.Many2one('finance.period', u'结账会计期间')
    date = fields.Date(u'生成凭证日期', required=True, default=_get_last_date)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    @api.onchange('date')
    def onchange_period_id(self):
        for wizard in self:
            wizard.period_id = self.env['finance.period'].with_context(
                module_name='checkout_wizard').get_period(wizard.date)

    @api.multi
    def button_checkout(self):
        ''' 月末结账：结账 按钮 '''
        for balance in self:
            if balance.period_id:
                if balance.period_id.is_closed:
                    raise UserError(u'本期间%s已结账' % balance.period_id.name)
                # 调用 生成科目余额表 向导的 计算上一个会计期间方法，得到 上一个会计期间
                last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(
                    balance.period_id)
                if last_period:
                    if not last_period.is_closed:
                        raise UserError(u'上一个会计期间%s未结账' % last_period.name)
                if balance.period_id.is_closed:
                    # TODO 此处重复，应去掉
                    raise UserError(u'本期间%s已结账' % balance.period_id.name)
                else:
                    voucher_obj = self.env['voucher']
                    voucher_ids = voucher_obj.search(
                        [('period_id', '=', balance.period_id.id),
                         ('state', '!=', 'cancel')])
                    draft_voucher_count = 0  # 未确认凭证个数
                    for voucher_id in voucher_ids:
                        if voucher_id.state != 'done':
                            draft_voucher_count += 1
                    if draft_voucher_count != 0:
                        raise UserError(u'该期间有%s张凭证未确认' % draft_voucher_count)
                    else:
                        voucher_line = []  # 生成的结账凭证行
                        account_obj = self.env['finance.account']
                        company_obj = self.env['res.company']
                        voucher_line_obj = self.env['voucher.line']
                        revenue_account_ids = account_obj.search(
                            [('costs_types', '=', 'in')])  # 收入类科目
                        expense_account_ids = account_obj.search(
                            [('costs_types', '=', 'out')])  # 费用类科目
                        revenue_total = 0  # 收入类科目合计
                        expense_total = 0  # 费用类科目合计
                        for revenue_account_id in revenue_account_ids:
                            voucher_line_ids = voucher_line_obj.search([
                                ('account_id', '=', revenue_account_id.id),
                                ('voucher_id.period_id', '=', balance.period_id.id),
                                ('state', '=', 'done')])
                            credit_total = 0
                            for voucher_line_id in voucher_line_ids:
                                credit_total += voucher_line_id.credit - voucher_line_id.debit
                            revenue_total += credit_total
                            if credit_total != 0:  # 贷方冲借方
                                res = {
                                    'name': u'月末结账',
                                    'account_id': revenue_account_id.id,
                                    'debit': credit_total,
                                    'credit': 0,
                                }
                                voucher_line.append(res)
                        for expense_account_id in expense_account_ids:
                            voucher_line_ids = voucher_line_obj.search([
                                ('account_id', '=', expense_account_id.id),
                                ('voucher_id.period_id', '=', balance.period_id.id),
                                ('state', '=', 'done')])
                            debit_total = 0
                            for voucher_line_id in voucher_line_ids:
                                debit_total += voucher_line_id.debit - voucher_line_id.credit
                            expense_total += debit_total
                            if debit_total != 0:  # 借方冲贷方
                                res = {
                                    'name': u'月末结账',
                                    'account_id': expense_account_id.id,
                                    'debit': 0,
                                    'credit': debit_total,
                                }
                                voucher_line.append(res)
                        # 利润结余
                        year_profit_account = self.env.user.company_id.profit_account
                        remain_account = self.env.user.company_id.remain_account
                        if not year_profit_account:
                            raise UserError(u'公司本年利润科目未配置')
                        if not remain_account:
                            raise UserError(u'公司未分配利润科目未配置')
                        if (revenue_total - expense_total) > 0:
                            res = {
                                'name': u'利润结余',
                                'account_id': year_profit_account.id,
                                'debit': 0,
                                'credit': revenue_total - expense_total,
                            }
                            voucher_line.append(res)
                        if (revenue_total - expense_total) < 0:
                            res = {
                                'name': u'利润结余',
                                'account_id': year_profit_account.id,
                                'debit': expense_total - revenue_total,
                                'credit': 0,
                            }
                            voucher_line.append(res)
                        # 生成凭证
                        if voucher_line:
                            valus = {
                                'is_checkout': True,
                                'date': self.date,
                                'line_ids': [
                                    (0, 0, line) for line in voucher_line],
                            }
                            voucher_profit = voucher_obj.create(valus)
                            voucher_profit.voucher_done()
                    year_account = None
                    if balance.period_id.month == '12':
                        year_profit_ids = voucher_line_obj.search([
                            ('account_id', '=', year_profit_account.id),
                            ('voucher_id.period_id.year', '=', balance.period_id.year),
                            ('state', '=', 'done')])
                        year_total = 0
                        for year_profit_id in year_profit_ids:
                            year_total += (year_profit_id.credit -
                                           year_profit_id.debit)
                        precision = self.env['decimal.precision'].precision_get(
                            'Amount')
                        year_total = round(year_total, precision)
                        if year_total != 0:
                            year_line_ids = [{
                                'name': u'年度结余',
                                'account_id': remain_account.id,
                                'debit': 0,
                                'credit': year_total,
                            }, {
                                'name': u'年度结余',
                                'account_id': year_profit_account.id,
                                'debit': year_total,
                                'credit': 0,
                            }]
                            value = {'is_checkout': True,
                                     'date': balance.date,
                                     'line_ids': [
                                         (0, 0, line) for line in year_line_ids],
                                     }
                            year_account = voucher_obj.create(value)  # 创建结转凭证
                            year_account.voucher_done()  # 凭证确认
                    # 生成科目余额表
                    trial_wizard = self.env['create.trial.balance.wizard'].create({
                        'period_id': balance.period_id.id,
                    })
                    trial_wizard.create_trial_balance()
                    # 按用户设置重排结账会计期间凭证号（会计要求凭证号必须连续）
                    self.recreate_voucher_name(balance.period_id)
                    # 关闭会计期间
                    balance.period_id.is_closed = True
                    self.env['dupont'].fill(balance.period_id)
                    pre_period = last_period
                    while pre_period:
                        self.env['dupont'].fill(pre_period)
                        pre_period = self.env['create.trial.balance.wizard'].compute_last_period_id(
                            pre_period)
                    # 如果下一个会计期间没有，则创建。
                    next_period = self.env['create.trial.balance.wizard'].compute_next_period_id(
                        balance.period_id)
                    if not next_period:
                        if balance.period_id.month == '12':
                            self.env['finance.period'].create({'year': str(int(balance.period_id.year) + 1),
                                                               'month': '1', })
                        else:
                            self.env['finance.period'].create({'year': balance.period_id.year,
                                                               'month': str(int(balance.period_id.month) + 1), })
                    # 显示凭证
                    view = self.env.ref('finance.voucher_form')
                    if voucher_line or year_account:
                        # 因重置凭证号，查找最后一张结转凭证
                        voucher = self.env['voucher'].search(
                            [('is_checkout', '=', True),
                             ('period_id', '=', balance.period_id.id),
                             ('state', '=', 'done')], order="create_date desc",
                            limit=1)
                        return {
                            'name': u'月末结账',
                            'view_type': 'form',
                            'view_mode': 'form',
                            'views': [(view.id, 'form')],
                            'res_model': 'voucher',
                            'type': 'ir.actions.act_window',
                            'res_id': voucher_profit.id,
                        }

    # 反结账
    @api.multi
    def button_counter_checkout(self):
        for balance in self:
            if balance.period_id:
                if not balance.period_id.is_closed:
                    raise UserError(u'期间%s未结账' % balance.period_id.name)
                else:
                    next_period = self.env['create.trial.balance.wizard'].compute_next_period_id(
                        balance.period_id)
                    if next_period:
                        if next_period.is_closed:
                            raise UserError(u'下一个期间%s已结账！' % next_period.name)
                    # 重新打开会计期间
                    balance.period_id.is_closed = False
                    # 删除相关凭证及科目余额表
                    voucher_ids = self.env['voucher'].search([('is_checkout', '=', True),
                                                              ('period_id', '=', balance.period_id.id)])
                    for voucher_id in voucher_ids:
                        voucher_id.voucher_draft()
                        voucher_id.unlink()
                    trial_balance_objs = self.env['trial.balance'].search(
                        [('period_id', '=', balance.period_id.id)])
                    trial_balance_objs.unlink()
                old = self.env['dupont'].search(
                    [('period_id', '=', balance.period_id.id)])
                for o in old:
                    o.unlink()

    # 按用户设置重排结账会计期间凭证号（会计要求凭证号必须连续）
    @api.multi
    def recreate_voucher_name(self, period_id):
        # 取重排凭证设置
        # 是否重置凭证号
        context = dict(self.env.context or {})
        context['call_module'] = "checkout_wizard"
        auto_reset = self.env['ir.values'].get_default(
            'finance.config.settings', 'default_auto_reset')
        # 重置凭证间隔:年  月
        reset_period = self.env['ir.values'].get_default(
            'finance.config.settings', 'default_reset_period')
        # 重置后起始数字
        reset_init_number = self.env['ir.values'].get_default(
            'finance.config.settings', 'default_reset_init_number')
        if auto_reset is True:
            # 取ir.sequence中的会计凭证的参数
            force_company = self._context.get('force_company')
            if not force_company:
                force_company = self.env.user.company_id.id
            company_ids = self.env['res.company'].search([]).ids + [False]
            seq_ids = self.env['ir.sequence'].search(
                ['&', ('code', '=', 'voucher'), ('company_id', 'in', company_ids)])
            preferred_sequences = [
                s for s in seq_ids if s.company_id and s.company_id.id == force_company]
            seq_id = preferred_sequences[0] if preferred_sequences else seq_ids[0]
            voucher_obj = self.env['voucher']
            # 按年重置
            last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(
                period_id)
            last_voucher_number = 0
            if reset_period == 'year':
                if last_period:
                    while last_period and last_voucher_number < 1:
                        if not last_period.is_closed:
                            raise UserError(u'上一个期间%s未结账' % last_period.name)
                        if period_id.year != last_period.year:
                            # 按年，而且是第一个会计期间
                            last_voucher_number = reset_init_number
                        else:
                            # 查找上一期间最后凭证号
                            last_period_voucher_name = voucher_obj.search([('period_id', '=', last_period.id),
                                                                           ('state', '=', 'done')],
                                                                          order="create_date desc", limit=1).name
                            # 凭证号转换为数字
                            if last_period_voucher_name:  # 上一期间是否有凭证？
                                last_voucher_number = int(
                                    filter(str.isdigit, last_period_voucher_name.encode("utf-8"))) + 1
                            # else:
                            #    raise UserError(u'请核实上一个期间：%s是否有凭证！' % last_period.name)
                            last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(
                                last_period)
                else:
                    last_voucher_number = reset_init_number
                voucher_ids = voucher_obj.search(
                    [('period_id', '=', period_id.id), ('state', '=', 'done')], order='create_date')
                for voucher_id in voucher_ids:
                    # 产生凭证号
                    next_voucher_name = '%%0%sd' % seq_id.padding % last_voucher_number
                    last_voucher_number += 1
                    # 更新凭证号
                    voucher_id.with_context(context).write(
                        {'name': next_voucher_name})
            # 按月重置
            else:
                if last_period and not last_period.is_closed:
                    raise UserError(u'上一个期间%s未结账' % last_period.name)
                last_voucher_number = reset_init_number
                voucher_ids = voucher_obj.search(
                    [('period_id', '=', period_id.id), ('state', '=', 'done')], order='create_date')
                for voucher_id in voucher_ids:
                    # 产生凭证号
                    next_voucher_name = '%%0%sd' % seq_id.padding % last_voucher_number
                    # 更新凭证号,将老号写到变化表中去！
                    if voucher_id.name != next_voucher_name:
                        self.env['change.voucher.name'].create({
                            'period_id': self.period_id.id,
                            'before_voucher_name': voucher_id.name,
                            'after_voucher_name': next_voucher_name,
                        })
                    voucher_id.with_context(context).write(
                        {'name': next_voucher_name})
                    last_voucher_number += 1
