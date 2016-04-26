# -*- coding: utf-8 -*-

from openerp import models, fields, api
# from openerp.exceptions import except_orm
# from datetime import datetime
# import calendar

ISODATEFORMAT = '%Y-%m-%d'
ISODATETIMEFORMAT = "%Y-%m-%d %H:%M:%S"


class BalanceSheet(models.Model):
    _name = "balance.sheet"
    balance = fields.Char(u'资产')
    line_num = fields.Integer(u'行次')
    ending_balance = fields.Float(u'期末余额')
    ending_balance_formula = fields.Text(u'期末余额计算公式')
    beginning_balance_formula = fields.Text(u'年初余额计算公式')
    beginning_balance = fields.Float(u'年初余额')

    balance_two = fields.Char(u'资产')
    line_num_two = fields.Integer(u'行次')
    ending_balance_two = fields.Float(u'期末余额')
    ending_balance_two_formula = fields.Text(u'期末余额计算公式')
    beginning_balance_two_formula = fields.Text(u'年初余额计算公式')
    beginning_balance_two = fields.Float(u'年初余额')


class create_balance_sheet_wizard(models.TransientModel):
    _name = "create.balance.sheet.wizard"
    period_id = fields.Many2one('finance.period', string='会计期间')

    @api.multi
    def compute_balance(self, parameter_str, period_id, compute_field_list):
        if parameter_str:
            parameter_str_list = parameter_str.split('~')
            subject_vals = []
            subject_ids = self.env['finance.account'].search([('code', '>=', parameter_str_list[0]), ('code', '<=', parameter_str_list[1])])
            trial_balances = self.env['trial.balance'].search([('subject_name_id', 'in', [subject.id for subject in subject_ids]), ('period_id', '=', period_id.id)])
            for trial_balance in trial_balances:
                if trial_balance.subject_name_id.balance_directions == 'in':
                    subject_vals.append(trial_balance[compute_field_list[0]] - trial_balance[compute_field_list[1]])
                elif trial_balance.subject_name_id.balance_directions == 'out':
                    subject_vals.append(trial_balance[compute_field_list[1]] - trial_balance[compute_field_list[0]])
            return sum(subject_vals)

        else:
            return 0

    @api.multi
    def create_balance_sheet(self):
        balance_wizard = self.env['create.trial.balance.wizard'].create({'period_id': self.period_id.id})
        balance_wizard.create_trial_balance()
        view_id = self.env.ref('finance.balance_sheet_tree_wizard').id
        balance_sheet_objs = self.env['balance.sheet'].search([])
        period = self.env['finance.period'].search([('year', '=', self.period_id.year), ('month', '=', '1')])
        year_begain_field = ['initial_balance_debit', 'initial_balance_credit']
        current_period_field = ['ending_balance_debit', 'ending_balance_credit']
        for balance_sheet_obj in balance_sheet_objs:
            balance_sheet_obj.write({'beginning_balance': self.compute_balance(balance_sheet_obj.beginning_balance_formula, period, year_begain_field),
                                     'ending_balance': self.compute_balance(balance_sheet_obj.ending_balance_formula, self.period_id, current_period_field),
                                     'beginning_balance_two': self.compute_balance(balance_sheet_obj.beginning_balance_two_formula, period, year_begain_field),
                                     'ending_balance_two': self.compute_balance(balance_sheet_obj.ending_balance_two_formula, self.period_id, current_period_field)})
        return {
            'type': 'ir.actions.act_window',
            'name': '资产负债表',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'balance.sheet',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': self.period_id.id},
            'domain': [('id', 'in', [balance_sheet_obj.id for balance_sheet_obj in balance_sheet_objs])],
        }

    @api.multi
    def create_profit_statement(self):
        balance_wizard = self.env['create.trial.balance.wizard'].create({'period_id': self.period_id.id})
        balance_wizard.create_trial_balance()
        view_id = self.env.ref('finance.profit_statement_tree').id
        balance_sheet_objs = self.env['profit.statement'].search([])
        year_begain_field = ['cumulative_occurrence_debit', 'cumulative_occurrence_credit']
        current_period_field = ['current_occurrence_debit', 'current_occurrence_credit']
        for balance_sheet_obj in balance_sheet_objs:
            balance_sheet_obj.write({'cumulative_occurrence_balance': self.compute_profit(balance_sheet_obj.cumulative_occurrence_balance_formula, self.period_id, year_begain_field),
                                     'current_occurrence_balance': self.compute_profit(balance_sheet_obj.current_occurrence_balance_formula, self.period_id, current_period_field)})
        return {
            'type': 'ir.actions.act_window',
            'name': '资产负债表',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'profit.statement',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': self.period_id.id},
            'domain': [('id', 'in', [balance_sheet_obj.id for balance_sheet_obj in balance_sheet_objs])],
        }

    @api.multi
    def compute_profit(self, parameter_str, period_id, compute_field_list):
        if parameter_str:
            parameter_str_list = parameter_str.split('~')
            subject_vals = []
            subject_ids = self.env['finance.account'].search([('code', '>=', parameter_str_list[0]), ('code', '<=', parameter_str_list[1])])
            trial_balances = self.env['trial.balance'].search([('subject_name_id', 'in', [subject.id for subject in subject_ids]), ('period_id', '=', period_id.id)])
            for trial_balance in trial_balances:
                if trial_balance.subject_name_id.balance_directions == 'in':
                    subject_vals.append(trial_balance[compute_field_list[0]])
                elif trial_balance.subject_name_id.balance_directions == 'out':
                    subject_vals.append(trial_balance[compute_field_list[1]])
            return sum(subject_vals)
        else:
            return 0


class ProfitStatement(models.Model):
    _name = "profit.statement"
    balance = fields.Char(u'项目')
    line_num = fields.Integer(u'行次')
    cumulative_occurrence_balance = fields.Float(u'本年累计金额')
    cumulative_occurrence_balance_formula = fields.Text(u'本年累计金额计算参数')
    current_occurrence_balance_formula = fields.Text(u'本月累计金额计算参数')
    current_occurrence_balance = fields.Float(u'本月累计金额')
