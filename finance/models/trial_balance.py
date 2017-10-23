# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from math import fabs
import copy
import odoo.addons.decimal_precision as dp


class TrialBalance(models.Model):
    """科目余额表"""
    _name = "trial.balance"
    _order = 'subject_code'
    _description = u'科目余额表'

    @api.one
    @api.depends('cumulative_occurrence_debit', 'cumulative_occurrence_credit',
                 'ending_balance_debit', 'ending_balance_credit', 'subject_name_id')
    def _get_year_init(self):
        if self.subject_name_id.costs_types in ('in', 'out'):
            self.year_init_debit = self.year_init_credit = 0
            return True
        if self.subject_name_id.balance_directions == 'in':
            # 年初借 = 期末借 - 期末贷 - 本年借 + 本年贷
            self.year_init_debit = self.ending_balance_debit - self.ending_balance_credit - \
                self.cumulative_occurrence_debit + self.cumulative_occurrence_credit
            self.year_init_credit = 0
        else:
            # 年初贷 = 期末贷 - 期末借 - 本年贷 + 本年借
            self.year_init_credit = self.ending_balance_credit - self.ending_balance_debit - \
                self.cumulative_occurrence_credit + self.cumulative_occurrence_debit
            self.year_init_debit = 0

    period_id = fields.Many2one('finance.period', string=u'会计期间')
    subject_code = fields.Char(u'科目编码')
    subject_name_id = fields.Many2one('finance.account', string=u'科目')
    year_init_debit = fields.Float(u'年初余额(借方)', digits=dp.get_precision(
        'Amount'), default=0, compute=_get_year_init)
    year_init_credit = fields.Float(u'年初余额(贷方)', digits=dp.get_precision(
        'Amount'), default=0, compute=_get_year_init)
    initial_balance_debit = fields.Float(
        u'期初余额(借方)', digits=dp.get_precision('Amount'), default=0)
    initial_balance_credit = fields.Float(
        u'期初余额(贷方)', digits=dp.get_precision('Amount'), default=0)
    current_occurrence_debit = fields.Float(
        u'本期发生额(借方)', digits=dp.get_precision('Amount'), default=0)
    current_occurrence_credit = fields.Float(
        u'本期发生额(贷方)', digits=dp.get_precision('Amount'), default=0)
    ending_balance_debit = fields.Float(
        u'期末余额(借方)', digits=dp.get_precision('Amount'), default=0)
    ending_balance_credit = fields.Float(
        u'期末余额(贷方)', digits=dp.get_precision('Amount'), default=0)
    cumulative_occurrence_debit = fields.Float(
        u'本年累计发生额(借方)', digits=dp.get_precision('Amount'), default=0)
    cumulative_occurrence_credit = fields.Float(
        u'本年累计发生额(贷方)', digits=dp.get_precision('Amount'), default=0)


class CreateTrialBalanceWizard(models.TransientModel):
    """根据输入的期间 生成科目余额表的 向导 """
    _name = "create.trial.balance.wizard"
    _description = u'科目余额表的创建向导'

    @api.model
    def _default_period_id(self):
        return self._default_period_id_impl()

    @api.model
    def _default_period_id_impl(self):
        """
                        默认是当前会计期间
        :return: 当前会计期间的对象
        """
        return self.env['finance.period'].get_date_now_period_id()

    period_id = fields.Many2one(
        'finance.period', default=_default_period_id, string=u'会计期间', help=u'限定生成期间的范围')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def compute_last_period_id(self, period_id):
        """取得参数区间的上个期间"""
        if int(period_id.month) == 1:
            year = int(period_id.year) - 1
            month = 12
        else:
            year = period_id.year
            month = int(period_id.month) - 1
        return self.env['finance.period'].search([('year', '=', str(year)), ('month', '=', str(month))])

    @api.multi
    def compute_next_period_id(self, period_id):
        """取得输入期间的下一个期间"""
        if int(period_id.month) == 12:
            year = int(period_id.year) + 1
            month = 1
        else:
            year = period_id.year
            month = int(period_id.month) + 1
        return self.env['finance.period'].search([('year', '=', str(year)), ('month', '=', str(month))])

    @api.multi
    def get_period_balance(self, period_id):
        """取出本期发生额
            返回结果是 科目 借 贷
         """
        sql = '''select vol.account_id as account_id,
                    sum(vol.debit) as debit,
                    sum(vol.credit) as credit
                 from voucher as vo
                 left join voucher_line as vol
                 on vo.id = vol.voucher_id
                 where vo.period_id=%s
                 group by vol.account_id'''
        self.env.cr.execute(sql, (period_id,))
        return self.env.cr.dictfetchall()

    @api.multi
    def create_trial_balance(self):
        """ \
            生成科目余额表 \
            1.如果所选区间已经关闭则直接调出已有的科目余额表记录
            2.判断如果所选的区间的 前一个期间没有关闭则报错
            3.如果上一个区间不存在则报错
        """
        trial_balance_objs = self.env['trial.balance'].search(
            [('period_id', '=', self.period_id.id)])
        trial_balance_ids = [
            trial_balance_row.id for trial_balance_row in trial_balance_objs]
        if not self.period_id.is_closed:
            trial_balance_objs.unlink()
            last_period = self.compute_last_period_id(self.period_id)
            if last_period:
                if not last_period.is_closed:
                    raise UserError(u'期间%s未结账，无法取到%s期期初余额' %
                                    (last_period.name, self.period_id.name))
            period_id = self.period_id.id
            current_occurrence_dic_list = self.get_period_balance(period_id)
            trial_balance_dict = {}
            """把本期发生额的数量填写到  准备好的dict 中 """
            for current_occurrence in current_occurrence_dic_list:
                account = self.env['finance.account'].browse(
                    current_occurrence.get('account_id'))
                ending_balance_debit = ending_balance_credit = 0
                this_debit = current_occurrence.get('debit', 0) or 0
                this_credit = current_occurrence.get('credit', 0) or 0
                if account.balance_directions == 'in':
                    ending_balance_debit = this_debit - this_credit
                else:
                    ending_balance_credit = this_credit - this_debit
                account_dict = {'period_id': period_id,
                                'current_occurrence_debit': this_debit,
                                'current_occurrence_credit': this_credit,
                                'subject_code': account.code,
                                'initial_balance_credit': 0,
                                'initial_balance_debit': 0,
                                'ending_balance_debit': ending_balance_debit,
                                'ending_balance_credit': ending_balance_credit,
                                'cumulative_occurrence_debit': this_debit,
                                'cumulative_occurrence_credit': this_credit,
                                'subject_name_id': account.id}
                trial_balance_dict[account.id] = account_dict
            trial_balance_dict.update(self.construct_trial_balance_dict(
                trial_balance_dict, last_period))
            trial_balance_ids = [self.env['trial.balance'].create(vals).id for (key, vals) in
                                 trial_balance_dict.items()]
        view_id = self.env.ref('finance.trial_balance_tree').id
        if self.period_id == self.period_id.get_init_period():
            view_id = self.env.ref('finance.init_balance_tree').id

        return {
            'type': 'ir.actions.act_window',
            'name': u'科目余额表：' + self.period_id.name,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'trial.balance',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'domain': [('id', 'in', trial_balance_ids)]
        }

    def compute_trial_balance_data(self, trial_balance, last_period, subject_name_id, trial_balance_dict):
        ''' 获得 科目余额表 数据 '''
        initial_balance_credit = trial_balance.ending_balance_credit or 0
        initial_balance_debit = trial_balance.ending_balance_debit or 0
        this_debit = this_credit = ending_balance_credit = 0

        if subject_name_id in trial_balance_dict:  # 本月有发生额
            this_debit = trial_balance_dict[subject_name_id].get(
                'current_occurrence_debit', 0) or 0
            this_credit = trial_balance_dict[subject_name_id].get(
                'current_occurrence_credit', 0) or 0
            ending_balance_debit = initial_balance_debit + \
                this_debit - initial_balance_credit - this_credit
            if ending_balance_debit < 0:
                ending_balance_credit -= ending_balance_debit
                ending_balance_debit = 0
        else:
            ending_balance_credit = initial_balance_credit
            ending_balance_debit = initial_balance_debit
        # 本年累计发生额
        if self.period_id.year == last_period.year:
            cumulative_occurrence_credit = this_credit + \
                trial_balance.cumulative_occurrence_credit
            cumulative_occurrence_debit = this_debit + \
                trial_balance.cumulative_occurrence_debit
        else:
            cumulative_occurrence_credit = this_credit
            cumulative_occurrence_debit = this_debit

        return_vals = [initial_balance_credit, initial_balance_debit, ending_balance_credit,
                       ending_balance_debit, this_debit, this_credit, cumulative_occurrence_credit,
                       cumulative_occurrence_debit]
        return return_vals

    def construct_trial_balance_dict(self, trial_balance_dict, last_period):
        """ 结合上一期间的 数据 填写  trial_balance_dict(余额表 记录生成dict)   """
        currency_dict = copy.deepcopy(trial_balance_dict)
        for trial_balance in self.env['trial.balance'].search([('period_id', '=', last_period.id)]):
            subject_name_id = trial_balance.subject_name_id.id

            [initial_balance_credit, initial_balance_debit, ending_balance_credit, ending_balance_debit, this_debit,
             this_credit, cumulative_occurrence_credit, cumulative_occurrence_debit] = \
                self.compute_trial_balance_data(
                    trial_balance, last_period, subject_name_id, currency_dict)

            subject_code = trial_balance.subject_code
            currency_dict[trial_balance.subject_name_id.id] = {
                'initial_balance_credit': initial_balance_credit,
                'initial_balance_debit': initial_balance_debit,
                'ending_balance_credit': ending_balance_credit,
                'ending_balance_debit': ending_balance_debit,
                'current_occurrence_debit': this_debit,
                'current_occurrence_credit': this_credit,
                'cumulative_occurrence_credit': cumulative_occurrence_credit,
                'cumulative_occurrence_debit': cumulative_occurrence_debit,
                'subject_code': subject_code,
                'period_id': self.period_id.id,
                'subject_name_id': subject_name_id
            }
        return currency_dict


class CreateVouchersSummaryWizard(models.TransientModel):
    """创建 明细账或者总账的向导 """
    _name = "create.vouchers.summary.wizard"
    _description = u'明细账或总账创建向导'

    @api.model
    def _default_end_period_id(self):
        """
        默认是当前会计期间
        :return: 当前会计期间的对象
        """
        return self.env['finance.period'].get_date_now_period_id()

    @api.model
    def _default_begin_period_id(self):
        """
            默认是当前会计期间
            :return: 当前会计期间的对象
            """
        return self.env['finance.period'].get_year_fist_period_id()

    @api.model
    def _default_subject_name_id(self):
        return self.env['finance.account'].get_smallest_code_account()

    @api.model
    def _default_subject_name_end_id(self):
        return self.env['finance.account'].get_max_code_account()

    period_begin_id = fields.Many2one('finance.period', string=u'开始期间', default=_default_begin_period_id,
                                      help=u'默认是本年第一个期间')
    period_end_id = fields.Many2one(
        'finance.period', string=u'结束期间', default=_default_end_period_id, help=u'默认是当前期间')
    subject_name_id = fields.Many2one('finance.account', string=u'会计科目 从', default=_default_subject_name_id,
                                      help=u'默认是所有科目的最小code')
    subject_name_end_id = fields.Many2one('finance.account', string=u'到', default=_default_subject_name_end_id,
                                          help=u'默认是所有科目的最大code')
    no_occurred = fields.Boolean(
        u'有发生额', default=True, help=u'无发生额的科目不显示明细账，默认为不显示')
    no_balance = fields.Boolean(
        u'有余额', default=True, help=u'无余额的科目不显示明细账，默认为不显示')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.onchange('period_begin_id', 'period_end_id')
    def onchange_period(self):
        '''结束期间大于起始期间报错'''

        if self.env['finance.period'].period_compare(self.period_end_id, self.period_begin_id) < 0:
            self.period_end_id = self.period_begin_id
            return {'warning': {
                'title': u'错误',
                'message': u'结束期间必须大于等于开始期间!\n开始期间为:%s 结束期间为:%s' %
                           (self.period_begin_id.name, self.period_end_id.name),
            }}

    @api.multi
    def get_initial_balance(self, period, account_row):
        """取得期初余额"""
        vals_dict = {}
        if period:
            period_id = period.id
        else:
            period_id = False
        initial_balance_credit = 0
        initial_balance_debit = 0
        trial_balance_obj = self.env['trial.balance'].search(
            [('period_id', '=', period_id), ('subject_name_id', '=', account_row.id)])
        if trial_balance_obj:
            initial_balance_credit = trial_balance_obj.ending_balance_credit
            initial_balance_debit = trial_balance_obj.ending_balance_debit
        direction_tuple = self.judgment_lending(
            0, initial_balance_credit, initial_balance_debit)
        vals_dict.update({
            'date': False,
            'direction': direction_tuple[0],
            'balance': fabs(direction_tuple[1]),
            'summary': account_row.code + ' ' + account_row.name + u":" + u'期初余额'})
        return vals_dict

    @api.multi
    def judgment_lending(self, balance, balance_credit, balance_debit):
        """根据明细账的借贷 金额 判断出本条记录的余额 及方向，balance 为上一条记录余额
            传入参数 余额 ,贷方,借方
            :return:返回一个tuple (借贷平借贷方向 ,余额)
        """
        balance += balance_debit - balance_credit
        if balance > 0:
            direction = u'借'
        elif balance < 0:
            direction = u'贷'
        else:
            direction = u'平'
        return (direction, balance)

    @api.multi
    def get_year_balance(self, period, subject_name):
        """根据期间和科目名称 计算出本期合计 和本年累计 (已经关闭的期间)
        :param period 期间 subject_name 科目object
        return: [本期合计dict,本年合计dict ]
        """
        vals_dict = {}
        trial_balance_obj = self.env['trial.balance'].search(
            [('period_id', '=', period.id), ('subject_name_id', '=', subject_name.id)])
        if trial_balance_obj:
            cumulative_occurrence_credit = trial_balance_obj.cumulative_occurrence_credit
            cumulative_occurrence_debit = trial_balance_obj.cumulative_occurrence_debit
            current_occurrence_credit = trial_balance_obj.current_occurrence_credit
            current_occurrence_debit = trial_balance_obj.current_occurrence_debit
            ending_balance_debit = trial_balance_obj.ending_balance_debit
            ending_balance_credit = trial_balance_obj.ending_balance_credit
        else:
            cumulative_occurrence_credit = 0
            cumulative_occurrence_debit = 0
            current_occurrence_credit = 0
            current_occurrence_debit = 0
            ending_balance_debit = 0
            ending_balance_credit = 0
        # direction_tuple = self.judgment_lending(0, cumulative_occurrence_credit, cumulative_occurrence_debit)
        direction_tuple_period = self.judgment_lending(
            0, ending_balance_credit, ending_balance_debit)
        period_vals = {
            'date': False,
            'direction': direction_tuple_period[0],
            'period_id': period.id,
            'credit': current_occurrence_credit,
            'debit': current_occurrence_debit,
            'balance': fabs(direction_tuple_period[1]),
            'summary': subject_name.code + ' ' + subject_name.name + u":" + u'本期合计'}
        vals_dict.update({
            'date': False,
            'direction': direction_tuple_period[0],
            'balance': fabs(direction_tuple_period[1]),
            'period_id': False,
            'debit': cumulative_occurrence_debit,
            'credit': cumulative_occurrence_credit,
            'summary': subject_name.code + ' ' + subject_name.name + u":" + u'本年累计'})
        return [period_vals, vals_dict]

    @api.multi
    def get_current_occurrence_amount(self, period, subject_name):
        """计算出 本期的科目的 voucher_line的明细记录 """
        sql = ''' select vo.date as date, vo.id as voucher_id,COALESCE(vol.debit,0) as debit,vol.name
                  as summary,COALESCE(vol.credit,0) as credit
                  from voucher as vo left join voucher_line as vol
                  on vo.id = vol.voucher_id where vo.period_id=%s and  vol.account_id=%s
                  order by vo.name
                 '''
        self.env.cr.execute(sql, (period.id, subject_name.id))
        sql_results = self.env.cr.dictfetchall()
        last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(
            period)
        local_last_period = last_period
        initial_balance = self.get_initial_balance(
            local_last_period, subject_name)
        balance = 0  # 上一条记录余额
        for i in xrange(len(sql_results)):
            if i == 0:
                balance = initial_balance['balance']
                if initial_balance['direction'] == u'贷':
                    balance = -balance
            else:
                balance += sql_results[i - 1]['debit'] - \
                    sql_results[i - 1]['credit']
            direction_tuple = self.judgment_lending(
                balance, sql_results[i]['credit'], sql_results[i]['debit'])
            sql_results[i].update({'direction': direction_tuple[0],
                                   'balance': fabs(direction_tuple[1]),
                                   'period_id': period.id}
                                  )
        return sql_results

    @api.multi
    def get_unclose_year_balance(self, initial_balance_new, period, subject_name):
        """取得没有关闭的期间的 本期合计和 本年累计"""
        current_occurrence = {}
        sql = ''' select  sum(COALESCE(vol.debit,0)) as debit,sum(COALESCE(vol.credit,0)) as credit
         from voucher as vo left join voucher_line as vol
            on vo.id = vol.voucher_id where vo.period_id=%s and  vol.account_id=%s
                 group by vol.account_id'''
        self.env.cr.execute(sql, (period.id, subject_name.id))
        sql_results = self.env.cr.dictfetchall()
        current_credit = 0
        current_debit = 0
        if sql_results:
            current_credit = sql_results[0].get('credit', 0)
            current_debit = sql_results[0].get('debit', 0)
        # 本年累计
        # 查找累计区间,作本年累计
        year_balance_debit = year_balance_credit = 0
        compute_periods = self.env['finance.period'].search([('year', '=', str(period.year)),
                                                             ('month', '<=', str(period.month))])
        for line_period in compute_periods:
            sql = ''' select  sum(COALESCE(vol.debit,0)) as debit,sum(COALESCE(vol.credit,0)) as credit
             from voucher as vo left join voucher_line as vol
                on vo.id = vol.voucher_id where vo.period_id=%s and  vol.account_id=%s
                     group by vol.account_id'''
            self.env.cr.execute(sql, (line_period.id, subject_name.id))
            sql_results = self.env.cr.dictfetchall()
            if sql_results:
                year_balance_debit = year_balance_debit + \
                    sql_results[0].get('debit', 0)
                year_balance_credit = year_balance_credit + \
                    sql_results[0].get('credit', 0)
        direction_tuple_current = self.judgment_lending(initial_balance_new.get('balance', 0) if
                                                        initial_balance_new['direction'] == u'借' else -initial_balance_new.get(
            'balance', 0), current_credit, current_debit)
        current_occurrence.update({
            'date': False,
            'direction': direction_tuple_current[0],
            'balance': fabs(direction_tuple_current[1]),
            'debit': current_debit,
            'credit': current_credit,
            'period_id': period.id,
            'summary': subject_name.code + ' ' + subject_name.name + u":" + u'本期合计'
        })
        initial_balance_new.update({
            'date': False,
            'direction': direction_tuple_current[0],
            'balance': abs(direction_tuple_current[1]),
            'debit': year_balance_debit,
            'credit': year_balance_credit,
            'period_id': False,
            'summary': subject_name.code + ' ' + subject_name.name + u":" + u'本年累计'
        })
        return [current_occurrence, initial_balance_new]

    @api.multi
    def create_vouchers_summary(self):
        """创建出根据所选期间范围内的 明细帐记录"""
        last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(
            self.period_begin_id)
        if last_period:
            if not last_period.is_closed:
                raise UserError(u'期间%s未结账，无法取到%s期初余额' %
                                (last_period.name, self.period_begin_id.name))
        # period_end = self.env['create.trial.balance.wizard'].compute_next_period_id(self.period_end_id)
        vouchers_summary_ids = []
        subject_ids = self.env['finance.account'].search([('code', '>=', self.subject_name_id.code),
                                                          ('code', '<=', self.subject_name_end_id.code)])
        for account_line in subject_ids:
            local_last_period = last_period
            local_currcy_period = self.period_begin_id
            break_flag = True
            init = 1
            while break_flag:
                create_vals = []
                initial_balance = self.get_initial_balance(
                    local_last_period, account_line)  # 取上期间期初余额
                if init:
                    create_vals.append(initial_balance)  # 期初
                    init = 0
                occurrence_amount = self.get_current_occurrence_amount(
                    local_currcy_period, account_line)  # 本期明细
                create_vals += occurrence_amount
                if local_currcy_period.is_closed:
                    cumulative_year_occurrence = self.get_year_balance(
                        local_currcy_period, account_line)  # 本期合计 本年累计
                else:
                    cumulative_year_occurrence = self.get_unclose_year_balance(copy.deepcopy(initial_balance),
                                                                               local_currcy_period, account_line)
                create_vals += cumulative_year_occurrence
                if local_currcy_period.id == self.period_end_id.id:
                    break_flag = False
                local_last_period = local_currcy_period
                local_currcy_period = self.env['create.trial.balance.wizard'].compute_next_period_id(
                    local_currcy_period)
                if not local_currcy_period:  # 无下一期间，退出循环。
                    break_flag = False
                # 无发生额不显示
                if self.no_occurred and len(occurrence_amount) == 0:
                    continue
                # 无余额不显示
                if self.no_balance and cumulative_year_occurrence[0].get('credit') == 0 \
                        and cumulative_year_occurrence[0].get('debit') == 0:
                    continue
                for vals in create_vals:  # create_vals 值顺序为：期初余额  本期明细  本期本年累计
                    vouchers_summary_ids.append(
                        (self.env['vouchers.summary'].create(vals)).id)
        view_id = self.env.ref('finance.vouchers_summary_tree').id

        title = self.period_begin_id.name
        if self.period_end_id != self.period_begin_id:
            title += '-'
            title += self.period_end_id.name
        title += '_'
        title += self.subject_name_id.name
        if self.subject_name_end_id != self.subject_name_id:
            title += '-'
            title += self.subject_name_end_id.name

        return {
            'type': 'ir.actions.act_window',
            'name': u'明细账 : %s' % title,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'vouchers.summary',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'domain': [('id', 'in', vouchers_summary_ids)],
            'limit': 65535,
        }

    @api.multi
    def create_general_ledger_account(self):
        """创建总账"""
        last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(
            self.period_begin_id)
        if last_period and not last_period.is_closed:
            raise UserError(u'期间%s未结账，无法取到%s期初余额' %
                            (last_period.name, self.period_begin_id.name))
        # period_end = self.env['create.trial.balance.wizard'].compute_next_period_id(self.period_end_id)
        vouchers_summary_ids = []
        subject_ids = self.env['finance.account'].search([('code', '>=', self.subject_name_id.code),
                                                          ('code', '<=', self.subject_name_end_id.code)])
        for account_line in subject_ids:
            local_last_period = last_period
            local_currcy_period = self.period_begin_id
            break_flag = True
            while break_flag:
                create_vals = []
                initial_balance = self.get_initial_balance(
                    local_last_period, account_line)
                create_vals.append(initial_balance)
                if local_currcy_period.is_closed:
                    cumulative_year_occurrence = self.get_year_balance(
                        local_currcy_period, account_line)
                else:
                    cumulative_year_occurrence = self.get_unclose_year_balance(copy.deepcopy(initial_balance),
                                                                               local_currcy_period, account_line)
                create_vals += cumulative_year_occurrence
                if local_currcy_period.id == self.period_end_id.id:
                    break_flag = False
                local_last_period = local_currcy_period
                local_currcy_period = self.env['create.trial.balance.wizard'].compute_next_period_id(
                    local_currcy_period)
                if not local_currcy_period:  # 无下一期间，退出循环。
                    break_flag = False
                # 无余额不显示
                if self.no_balance and cumulative_year_occurrence[0].get('credit') == 0 \
                        and cumulative_year_occurrence[0].get('debit') == 0:
                    continue
                for vals in create_vals:
                    del vals['date']
                    vouchers_summary_ids.append(
                        (self.env['general.ledger.account'].create(vals)).id)

        view_id = self.env.ref('finance.general_ledger_account_tree').id

        title = self.period_begin_id.name
        if self.period_end_id != self.period_begin_id:
            title += '-'
            title += self.period_end_id.name
        title += '_'
        title += self.subject_name_id.name
        if self.subject_name_end_id != self.subject_name_id:
            title += '-'
            title += self.subject_name_end_id.name

        return {
            'type': 'ir.actions.act_window',
            'name': u'总账 %s' % title,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'general.ledger.account',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'domain': [('id', 'in', vouchers_summary_ids)],
            'limit': 65535,
        }


class VouchersSummary(models.TransientModel):
    """明细帐"""
    _name = 'vouchers.summary'
    _description = u'明细账'

    date = fields.Date(u'日期', help=u'日期')
    period_id = fields.Many2one('finance.period', string=u'会计期间', help=u'会计期间')
    voucher_id = fields.Many2one('voucher', u'凭证字号', help=u'凭证字号')
    summary = fields.Char(u'摘要', help=u'从凭证中获取到对应的摘要')
    direction = fields.Char(u'方向', help=u'会计术语,主要方向借、贷、平, 当借方金额大于贷方金额 方向为借\n\
     ，当贷方金额大于借方金额 方向为贷\n  借贷相等时 方向为平')
    debit = fields.Float(u'借方金额', help=u'借方金额')
    credit = fields.Float(u'贷方金额', help=u'贷方金额')
    balance = fields.Float(u'余额', help=u'一般显示为正数，计算方式：当方向为借时 \
                                   余额= 借方金额-贷方金额， 当方向为贷时 余额= 贷方金额-借方金额')

    @api.multi
    def view_detail_voucher(self):
        '''查看凭证明细按钮'''
        view = self.env.ref('finance.voucher_form')
        return {
            'name': u'会计凭证明细',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view.id, 'form')],
            'res_model': 'voucher',
            'type': 'ir.actions.act_window',
            'res_id': self.voucher_id.id,
        }


class GeneralLedgerAccount(models.TransientModel):
    """总账"""
    _name = 'general.ledger.account'
    _description = u'总账'

    period_id = fields.Many2one(
        'finance.period', string=u'会计期间',  help=u'记录本条记录的期间!')
    summary = fields.Char(u'摘要', help=u'摘要')
    direction = fields.Char(u'方向', help=u'会计术语,主要方向借、贷、平, 当借方金额大于贷方金额 方向为借\n\
     ，当贷方金额大于借方金额 方向为贷\n  借贷相等时 方向为平')
    debit = fields.Float(u'借方金额', help=u'借方金额')
    credit = fields.Float(u'贷方金额', help=u'贷方金额')
    balance = fields.Float(u'余额', help=u'一般显示为正数，计算方式：当方向为借时\
                                   余额= 借方金额-贷方金额， 当方向为贷时 余额= 贷方金额-借方金额')
