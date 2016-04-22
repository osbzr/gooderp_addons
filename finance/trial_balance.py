# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm


class TrialBalance(models.Model):
    _name = "trial.balance"

    period_id = fields.Many2one('finance.period', string='会计期间')
    subject_code = fields.Char(u'科目编码')
    subject_name_id = fields.Many2one('finance.account', string='科目名称')
    initial_balance_debit = fields.Float(u'期初余额', child_string=" 借方")
    initial_balance_credit = fields.Float(u'期初余额(贷方)', child_string="贷方")
    current_occurrence_debit = fields.Float(u'本期发生额', child_string="借方")
    current_occurrence_credit = fields.Float(u'本期发生额(贷方)', child_string="贷方")
    ending_balance_debit = fields.Float(u'期末余额', child_string="借方")
    ending_balance_credit = fields.Float(u'期末余额(贷方)', child_string="贷方")
    cumulative_occurrence_debit = fields.Float(u'本年累计发生额', child_string="借方")
    cumulative_occurrence_credit = fields.Float(u'本年累计发生额(贷方)', child_string="贷方")


class CreateTrialBalanceWizard(models.TransientModel):
    _name = "create.trial.balance.wizard"
    period_id = fields.Many2one('finance.period', string='会计期间')

    @api.multi
    def compute_last_period_id(self, period_id):
        if self.period_id.month == 1:
            year = int(self.period_id.year) - 1
            month = 12
        else:
            year = self.period_id.year
            month = int(self.period_id.month) - 1
        return self.env['finance.period'].search([('year', '=', year), ('month', '=', month)])

    @api.multi
    def get_period_balance(self, period_id):
        """取出本期发生额"""
        sql = ''' select vol.account_id as account_id,sum(vol.debit) as debit,  sum(vol.credit) as credit  from voucher as vo left join voucher_line as vol
            on vo.id = vol.voucher_id where vo.period_id=%s
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
        trial_balance_objs = self.env['trial.balance'].search([('period_id', '=', self.period_id.id)])
        trial_balance_ids = [balance.id for balance in trial_balance_objs]
        if not self.period_id.is_closed:
            trial_balance_objs.unlink()
            last_period = self.compute_last_period_id(self.period_id)
            if not last_period:
                raise except_orm(u'错误', u'上一个期间不存在,无法取到期初余额')
            if not last_period.is_closed:
                raise except_orm(u'错误', u'前一期间未结账，无法取到期初余额')
            period_id = self.period_id.id
            current_occurrence_dic_list = self.get_period_balance(period_id)
            trial_balance_dict = {}
            """把本期发生额的数量填写到  准备好的dict 中 """
            for current_occurrence in current_occurrence_dic_list:
                account = self.env['finance.account'].browse(current_occurrence.get('account_id'))

                account_dict = {'period_id': period_id, 'current_occurrence_debit': current_occurrence.get('debit'),
                                'current_occurrence_credit': current_occurrence.get('credit'), 'subject_code': account.code,
                                'initial_balance_credit': 0, 'initial_balance_debit': 0,
                                'ending_balance_credit': current_occurrence.get('credit'), 'ending_balance_debit': current_occurrence.get('debit'),
                                'cumulative_occurrence_credit': current_occurrence.get('credit'), 'cumulative_occurrence_debit': current_occurrence.get('debit'),
                                'subject_name_id': current_occurrence.get('account_id')}
                trial_balance_dict[current_occurrence.get('account_id')] = account_dict
            """ 结合上一期间的 数据 填写  trial_balance_dict(余额表 记录生成dict)   """
            for trial_balance in self.env['trial.balance'].search([('period_id', '=', last_period.id)]):
                initial_balance_credit = trial_balance.ending_balance_credit
                initial_balance_debit = trial_balance.ending_balance_debit
                subject_name_id = trial_balance.subject_name_id.id
                if subject_name_id in trial_balance_dict:
                    ending_balance_credit = trial_balance_dict[subject_name_id].get('current_occurrence_credit') + initial_balance_credit
                    ending_balance_debit = trial_balance_dict[subject_name_id].get('current_occurrence_debit') + initial_balance_debit
                    cumulative_occurrence_credit = trial_balance_dict[subject_name_id].get('current_occurrence_credit') + trial_balance.cumulative_occurrence_credit
                    cumulative_occurrence_debit = trial_balance_dict[subject_name_id].get('current_occurrence_debit') + trial_balance.cumulative_occurrence_debit
                else:
                    ending_balance_credit = initial_balance_credit
                    ending_balance_debit = initial_balance_debit
                    cumulative_occurrence_credit = trial_balance.cumulative_occurrence_credit
                    cumulative_occurrence_debit = trial_balance.cumulative_occurrence_debit

                subject_code = trial_balance.subject_code
                trial_balance_dict[subject_name_id] = {
                    'initial_balance_credit': initial_balance_credit,
                    'initial_balance_debit': initial_balance_debit,
                    'ending_balance_credit': ending_balance_credit,
                    'ending_balance_debit': ending_balance_debit,
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
            'domain': [('id', 'in', trial_balance_ids)],
        }

    @api.multi
    def create_vouchers_summary(self):

        return {}


class VouchersSummary(models.TransientModel):
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
