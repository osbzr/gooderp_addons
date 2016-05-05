# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm
from datetime import datetime
import calendar

ISODATEFORMAT = '%Y-%m-%d'
ISODATETIMEFORMAT = "%Y-%m-%d %H:%M:%S"


class TrialBalance(models.Model):
    """科目余额表"""
    _name = "trial.balance"

    period_id = fields.Many2one('finance.period', string='会计期间')
    subject_code = fields.Char(u'科目编码')
    subject_name_id = fields.Many2one('finance.account', string='科目名称')
    initial_balance_debit = fields.Float(u'期初余额(借方)', default=0)
    initial_balance_credit = fields.Float(u'期初余额(贷方)', default=0)
    current_occurrence_debit = fields.Float(u'本期发生额(借方)', default=0)
    current_occurrence_credit = fields.Float(u'本期发生额(贷方)', default=0)
    ending_balance_debit = fields.Float(u'期末余额(借方)', default=0)
    ending_balance_credit = fields.Float(u'期末余额(贷方)', default=0)
    cumulative_occurrence_debit = fields.Float(u'本年累计发生额(借方)', default=0)
    cumulative_occurrence_credit = fields.Float(u'本年累计发生额(贷方)', default=0)


class CreateTrialBalanceWizard(models.TransientModel):
    """生成科目余额表的 向导 根据输入的期间"""
    _name = "create.trial.balance.wizard"
    period_id = fields.Many2one('finance.period', string='会计期间')

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
        sql = ''' select vol.account_id as account_id,sum(vol.debit) as debit,  sum(vol.credit) as credit  from voucher as vo left join voucher_line as vol
            on vo.id = vol.voucher_id where vo.period_id=%s
                 group by vol.account_id'''
        self.env.cr.execute(sql, (period_id,))
        return self.env.cr.dictfetchall()

    @api.multi
    def compute_ending_balance(self, ending_credit, ending_debit):
        """计算出科目余额表的 期末余额(传入的是  )"""
        if ending_credit > ending_debit:
            ending_credit = ending_credit - ending_debit
            ending_debit = 0
        else:
            ending_credit = 0
            ending_debit = ending_debit - ending_credit
        return [ending_credit, ending_debit]

    @api.multi
    def create_trial_balance(self):
        """ \
            生成科目余额表 \
            1.如果所选区间已经关闭则直接调出已有的科目余额表记录
            2.判断如果所选的区间的 前一个期间没有关闭则报错
            3.如果上一个区间不存在则报错

        """
        trial_balance_objs = self.env['trial.balance'].search([('period_id', '=', self.period_id.id)])
        trial_balance_ids = [balance.id for balance in trial_balance_objs]
        if not self.period_id.is_closed:
            trial_balance_objs.unlink()
            last_period = self.compute_last_period_id(self.period_id)
            if last_period:
                last_period_id = last_period.id
                if not last_period.is_closed:
                    raise except_orm(u'错误', u'前一期间未结账，无法取到期初余额')
            else:
                last_period_id = False
            period_id = self.period_id.id
            current_occurrence_dic_list = self.get_period_balance(period_id)
            trial_balance_dict = {}
            """把本期发生额的数量填写到  准备好的dict 中 """
            for current_occurrence in current_occurrence_dic_list:
                account = self.env['finance.account'].browse(current_occurrence.get('account_id'))
                ending_balance_result = self.compute_ending_balance(current_occurrence.get('credit', 0) or 0, current_occurrence.get('debit', 0) or 0)
                account_dict = {'period_id': period_id, 'current_occurrence_debit': current_occurrence.get('debit', 0) or 0,
                                'current_occurrence_credit': current_occurrence.get('credit') or 0, 'subject_code': account.code,
                                'initial_balance_credit': 0, 'initial_balance_debit': 0,
                                'ending_balance_credit': ending_balance_result[0], 'ending_balance_debit': ending_balance_result[1],
                                'cumulative_occurrence_credit': current_occurrence.get('credit', 0) or 0, 'cumulative_occurrence_debit': current_occurrence.get('debit', 0) or 0,
                                'subject_name_id': current_occurrence.get('account_id')}
                trial_balance_dict[current_occurrence.get('account_id')] = account_dict

            """ 结合上一期间的 数据 填写  trial_balance_dict(余额表 记录生成dict)   """
            for trial_balance in self.env['trial.balance'].search([('period_id', '=', last_period_id)]):
                initial_balance_credit = trial_balance.ending_balance_credit or 0
                initial_balance_debit = trial_balance.ending_balance_debit or 0
                subject_name_id = trial_balance.subject_name_id.id
                if subject_name_id in trial_balance_dict:
                    ending_balance_credit = trial_balance_dict[subject_name_id].get('current_occurrence_credit', 0) + initial_balance_credit
                    ending_balance_debit = trial_balance_dict[subject_name_id].get('current_occurrence_debit', 0) + initial_balance_debit
                    cumulative_occurrence_credit = trial_balance_dict[subject_name_id].get('current_occurrence_credit', 0) + trial_balance.cumulative_occurrence_credit
                    cumulative_occurrence_debit = trial_balance_dict[subject_name_id].get('current_occurrence_debit', 0) + trial_balance.cumulative_occurrence_debit
                else:
                    ending_balance_credit = initial_balance_credit
                    ending_balance_debit = initial_balance_debit
                    cumulative_occurrence_credit = trial_balance.cumulative_occurrence_credit or 0
                    cumulative_occurrence_debit = trial_balance.cumulative_occurrence_debit or 0
                ending_balance_result = self.compute_ending_balance(ending_balance_credit, ending_balance_debit)
                subject_code = trial_balance.subject_code
                trial_balance_dict[subject_name_id] = {
                    'initial_balance_credit': initial_balance_credit,
                    'initial_balance_debit': initial_balance_debit,
                    'ending_balance_credit': ending_balance_result[0],
                    'ending_balance_debit': ending_balance_result[1],
                    'cumulative_occurrence_credit': cumulative_occurrence_credit,
                    'cumulative_occurrence_debit': cumulative_occurrence_debit,
                    'subject_code': subject_code,
                    'period_id': period_id,
                    'subject_name_id': subject_name_id
                }
            trial_balance_ids = [self.env['trial.balance'].create(vals).id for (key, vals) in trial_balance_dict.items()]
        view_id = self.env.ref('finance.trial_balance_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': '期末余额表',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'trial.balance',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'domain': [('id', 'in', trial_balance_ids)]
        }


class CreateVouchersSummaryWizard(models.TransientModel):
    """创建 明细账或者总账的向导 """
    _name = "create.vouchers.summary.wizard"
    period_begin_id = fields.Many2one('finance.period', string='开始期间')
    period_end_id = fields.Many2one('finance.period', string='结束期间')
    subject_name_id = fields.Many2one('finance.account', string='科目名称')

    @api.multi
    @api.onchange('period_begin_id', 'period_end_id')
    def onchange_period(self):
        '''结束期间大于起始期间报错'''

        if self.period_end_id and self.period_begin_id and  \
                (self.period_begin_id.year > self.period_end_id.year or self.period_begin_id.month > self.period_end_id.month):
            self.period_end_id = self.period_begin_id
            return {'warning': {
                'title': u'错误',
                'message': u'结束期间必须大于等于开始期间!',
            }}

    @api.multi
    def get_initial_balance(self, period, local_currcy_period, subject_name):
        """取得期初余额"""
        vals_dict = {}
        if period:
            period_id = period.id
        else:
            period_id = False
        trial_balance_obj = self.env['trial.balance'].search([('period_id', '=', period_id), ('subject_name_id', '=', subject_name)])
        if trial_balance_obj:
            initial_balance_credit = trial_balance_obj.ending_balance_credit
            initial_balance_debit = trial_balance_obj.ending_balance_debit
        else:
            initial_balance_credit = 0
            initial_balance_debit = 0

        direction_tuple = self.judgment_lending(initial_balance_credit, initial_balance_debit)
        vals_dict.update({
            'date': False,
            'direction': direction_tuple[0],
            'balance': direction_tuple[1],
            'subject_name_id': subject_name,
            'period_id': local_currcy_period.id,
            'summary': u'期初余额'})
        return vals_dict

    @api.multi
    def judgment_lending(self, balance_credit, balance_debit):
        """根据明细账的借贷 金额 判断出本条记录的余额 及方向"""
        if balance_credit > balance_debit:
            direction = '贷'
            balance = balance_credit - balance_debit
        elif balance_credit < balance_debit:
            direction = '借'
            balance = balance_debit - balance_credit
        else:
            direction = '平'
            balance = 0
        return (direction, balance)

    # @api.multi
    # def get_ending_balance(self, period, subject_name):
    #     vals_dict = {}
    #     trial_balance_obj = self.env['trial.balance'].search([('period_id', '=', period.id), ('subject_name_id', '=', subject_name)])
    #     if trial_balance_obj:
    #         print "====19"
    #         ending_balance_credit = trial_balance_obj.ending_balance_credit
    #         ending_balance_debit = trial_balance_obj.ending_balance_debit
    #     else:
    #         print "====20"
    #         ending_balance_credit = 0
    #         ending_balance_debit = 0

    #     direction_tuple = self.judgment_lending(ending_balance_credit, ending_balance_debit)
    #     vals_dict.update({
    #         'date': '%s-%s-01' % (period.year, period.month),
    #         'direction': direction_tuple[0],
    #         'balance': direction_tuple[1],
    #         'debit': ending_balance_debit,
    #         'credit': ending_balance_credit,
    #         'summary': u'期末余额'})
    #     return vals_dict

    @api.multi
    def get_year_balance(self, period, subject_name):
        """根据期间和科目名称 计算出本期合计 和本年累计 (已经关闭的期间)"""
        vals_dict = {}
        trial_balance_obj = self.env['trial.balance'].search([('period_id', '=', period.id), ('subject_name_id', '=', subject_name.id)])
        if trial_balance_obj:
            cumulative_occurrence_credit = trial_balance_obj.cumulative_occurrence_credit
            cumulative_occurrence_debit = trial_balance_obj.cumulative_occurrence_debit
            current_occurrence_credit = trial_balance_obj.current_occurrence_credit
            current_occurrence_debit = trial_balance_obj.current_occurrence_debit
        else:
            cumulative_occurrence_credit = 0
            cumulative_occurrence_debit = 0
            current_occurrence_credit = 0
            current_occurrence_debit = 0

        direction_tuple = self.judgment_lending(cumulative_occurrence_credit, cumulative_occurrence_debit)
        direction_tuple_period = self.judgment_lending(current_occurrence_credit, current_occurrence_debit)
        period_vals = {
            'date': False,
            'direction': direction_tuple_period[0],
            'credit': current_occurrence_credit,
            'subject_name_id': subject_name.id,
            'period_id': period.id,
            'debit': current_occurrence_debit,
            'balance': direction_tuple_period[1],
            'summary': '本期合计'}
        vals_dict.update({
            'date': False,
            'direction': direction_tuple[0],
            'balance': direction_tuple[1],
            'subject_name_id': subject_name.id,
            'period_id': period.id,
            'debit': cumulative_occurrence_debit,
            'credit': cumulative_occurrence_credit,
            'summary': u'本年累计发生额'})
        return [period_vals, vals_dict]

    @api.multi
    def get_current_occurrence_amount(self, period, subject_name):
        """计算出 本期的科目的 voucher_line的明细记录 """
        sql = ''' select vo.date as date, vo.id as voucher_id,COALESCE(vol.debit,0) as debit,vol.name as summary,COALESCE(vol.credit,0) as credit
         from voucher as vo left join voucher_line as vol
            on vo.id = vol.voucher_id where vo.period_id=%s and  vol.account_id=%s
                 '''
        self.env.cr.execute(sql, (period.id, subject_name.id))
        sql_results = self.env.cr.dictfetchall()
        for i in xrange(len(sql_results)):
            direction_tuple = self.judgment_lending(sql_results[i]['credit'], sql_results[i]['debit'])
            sql_results[i].update({'direction': direction_tuple[0],
                                   'balance': direction_tuple[1],
                                   'subject_name_id': subject_name.id,
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
            if initial_balance_new.get('direction') == '借':
                year_balance_debit = sql_results[0].get('debit', 0) + initial_balance_new.get('balance', 0)
                year_balance_credit = sql_results[0].get('credit', 0)
            else:
                year_balance_debit = sql_results[0].get('debit', 0)
                year_balance_credit = sql_results[0].get('credit', 0) + initial_balance_new.get('balance', 0)
        else:
            if initial_balance_new.get('direction') == '借':
                year_balance_debit = initial_balance_new.get('balance', 0)
                year_balance_credit = 0
            else:
                year_balance_debit = 0
                year_balance_credit = initial_balance_new.get('balance', 0)
        direction_tuple = self.judgment_lending(year_balance_credit, year_balance_debit)
        direction_tuple_current = self.judgment_lending(current_credit, current_debit)
        current_occurrence.update({
            'date': False,
            'direction': direction_tuple_current[0],
            'balance': direction_tuple_current[1],
            'debit': current_debit,
            'credit': current_credit,
            'subject_name_id': subject_name.id,
            'period_id': period.id,
            'summary': u'本期发生额'
        })
        initial_balance_new.update({
            'date': False,
            'direction': direction_tuple[0],
            'balance': direction_tuple[1],
            'debit': year_balance_debit,
            'subject_name_id': subject_name.id,
            'period_id': period.id,
            'credit': year_balance_credit,
            'summary': u'本年累计发生额'
        })
        return [current_occurrence, initial_balance_new]

    @api.multi
    def create_vouchers_summary(self):
        """创建出根据所选期间范围内的 明细帐记录"""
        last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(self.period_begin_id)
        if last_period:
            if not last_period.is_closed:
                raise except_orm(u'错误', u'前一期间未结账，无法取到期初余额')
        # period_end = self.env['create.trial.balance.wizard'].compute_next_period_id(self.period_end_id)
        local_last_period = last_period
        local_currcy_period = self.period_begin_id
        vouchers_summary_ids = []
        break_flag = True
        while (break_flag):
            create_vals = []
            initial_balance = self.get_initial_balance(local_last_period, local_currcy_period, self.subject_name_id.id)
            create_vals.append(initial_balance)
            occurrence_amount = self.get_current_occurrence_amount(local_currcy_period, self.subject_name_id)
            create_vals += occurrence_amount
            if local_currcy_period.id != self.period_end_id.id:
                cumulative_year_occurrence = self.get_year_balance(local_currcy_period, self.subject_name_id)
            else:
                cumulative_year_occurrence = self.get_unclose_year_balance(initial_balance.copy(), local_currcy_period, self.subject_name_id)
            create_vals += cumulative_year_occurrence
            if local_currcy_period.id == self.period_end_id.id:
                break_flag = False
            local_last_period = local_currcy_period
            local_currcy_period = self.env['create.trial.balance.wizard'].compute_next_period_id(local_currcy_period)
            for vals in create_vals:
                vouchers_summary_ids.append((self.env['vouchers.summary'].create(vals)).id)
        view_id = self.env.ref('finance.vouchers_summary_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': '期末余额表',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'vouchers.summary',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'domain': [('id', 'in', vouchers_summary_ids)]
        }

    @api.multi
    def create_general_ledger_account(self):
        """创建总账"""
        last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(self.period_begin_id)
        if not last_period:
            raise except_orm(u'错误', u'上一个期间不存在,无法取到期初余额')
        if not last_period.is_closed:
            raise except_orm(u'错误', u'前一期间未结账，无法取到期初余额')
        # period_end = self.env['create.trial.balance.wizard'].compute_next_period_id(self.period_end_id)
        local_last_period = last_period
        local_currcy_period = self.period_begin_id
        vouchers_summary_ids = []
        break_flag = True
        while (break_flag):
            create_vals = []
            initial_balance = self.get_initial_balance(local_last_period, local_currcy_period, self.subject_name_id.id)
            create_vals.append(initial_balance)
            if local_currcy_period.id != self.period_end_id.id:
                cumulative_year_occurrence = self.get_year_balance(local_currcy_period, self.subject_name_id)
            else:
                cumulative_year_occurrence = self.get_unclose_year_balance(initial_balance.copy(), local_currcy_period, self.subject_name_id)
            create_vals += cumulative_year_occurrence
            if local_currcy_period.id == self.period_end_id.id:
                break_flag = False
            local_last_period = local_currcy_period
            local_currcy_period = self.env['create.trial.balance.wizard'].compute_next_period_id(local_currcy_period)
            for vals in create_vals:
                del vals['date']
                if vals.get('voucher_id'):
                    del vals['date']
                vouchers_summary_ids.append((self.env['general.ledger.account'].create(vals)).id)
        view_id = self.env.ref('finance.vouchers_summary_tree').id
        view_id = self.env.ref('finance.general_ledger_account_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': '期末余额表',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'general.ledger.account',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'domain': [('id', 'in', vouchers_summary_ids)]
        }


class VouchersSummary(models.TransientModel):
    """总账"""
    _name = 'vouchers.summary'
    date = fields.Date(u'日期')
    subject_name_id = fields.Many2one('finance.account', string='科目名称')
    period_id = fields.Many2one('finance.period', string='会计区间')
    voucher_id = fields.Many2one('voucher', u'凭证字号')
    summary = fields.Char(u'摘要')
    direction = fields.Char(u'方向')
    debit = fields.Float(u'借方金额')
    credit = fields.Float(u'贷方金额')
    balance = fields.Float(u'余额')


class GeneralLedgerAccount(models.TransientModel):
    """明细帐"""
    _name = 'general.ledger.account'
    period_id = fields.Many2one('finance.period', string='会计期间')
    subject_name_id = fields.Many2one('finance.account', string='科目名称')
    summary = fields.Char(u'摘要')
    direction = fields.Char(u'方向')
    debit = fields.Float(u'借方金额')
    credit = fields.Float(u'贷方金额')
    balance = fields.Float(u'余额')
