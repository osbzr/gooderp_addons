# -*- coding: utf-8 -*-

from odoo import models, fields, api
from math import fabs
import calendar


class BalanceSheet(models.Model):
    """资产负债表模板
    模板用来定义最终输出的 资产负债表的格式,
     每行的 科目的顺序 科目的大分类的所属的子科目的顺序
    -- 本模板适合中国会计使用.
    """

    _name = "balance.sheet"
    _order = "sequence,id"
    _description = u'资产负债表模板'

    sequence = fields.Integer(u'序号')
    line = fields.Integer(u'序号', required=True, help=u'资产负债表的行次')
    balance = fields.Char(u'资产')
    line_num = fields.Char(u'行次', help=u'此处行次并不是出报表的实际的行数,只是显示用的用来符合国人习惯')
    ending_balance = fields.Float(u'期末数')
    balance_formula = fields.Text(
        u'科目范围', help=u'设定本行的资产负债表的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    beginning_balance = fields.Float(u'年初数')

    balance_two = fields.Char(u'负债和所有者权益')
    line_num_two = fields.Char(u'行次', help=u'此处行次并不是出报表的实际的行数,只是显示用的用来符合国人习惯')
    ending_balance_two = fields.Float(u'期末数')
    balance_two_formula = fields.Text(
        u'科目范围', help=u'设定本行的资产负债表的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    beginning_balance_two = fields.Float(u'年初数', help=u'报表行本年的年余额')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())


class CreateBalanceSheetWizard(models.TransientModel):
    """创建资产负债 和利润表的 wizard"""
    _name = "create.balance.sheet.wizard"
    _description = u'资产负债表和利润表的向导'

    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.model
    def _default_period_domain(self):
        """
        用来设定期间的 可选的范围(这个是一个范围)
        :return: domain条件
        """
        period_domain_setting = self.env['ir.values'].get_default(
            'finance.config.settings', 'default_period_domain')
        return [('is_closed', '!=', False)] if period_domain_setting == 'cannot' else []

    @api.model
    def _default_period_id(self):

        return self._default_period_id_impl()

    def _default_period_id_impl(self):
        """
                        默认是当前会计期间
        :return: 当前会计期间的对象
        """
        return self.env['finance.period'].get_date_now_period_id()

    period_id = fields.Many2one('finance.period', string=u'会计期间', domain=_default_period_domain,
                                default=_default_period_id, help=u'用来设定报表的期间')

    @api.multi
    def compute_balance(self, parameter_str, period_id, compute_field_list):
        """根据所填写的 科目的code 和计算的字段 进行计算对应的资产值"""
        if parameter_str:
            parameter_str_list = parameter_str.split('~')
            subject_vals = []
            if len(parameter_str_list) == 1:
                subject_ids = self.env['finance.account'].search(
                    [('code', '=', parameter_str_list[0]), ('account_type', '!=', 'view')])
            else:
                subject_ids = self.env['finance.account'].search(
                    [('code', '>=', parameter_str_list[0]), ('code', '<=', parameter_str_list[1]),
                     ('account_type', '!=', 'view')])
            trial_balances = self.env['trial.balance'].search([('subject_name_id', 'in', [
                subject.id for subject in subject_ids]), ('period_id', '=', period_id.id)])
            for trial_balance in trial_balances:
                # 根据参数code 对应的科目的 方向 进行不同的操作
                #  trial_balance.subject_name_id.costs_types == 'assets'解决：累计折旧 余额记贷方
                if trial_balance.subject_name_id.costs_types == 'assets' or trial_balance.subject_name_id.costs_types == 'cost':
                    subject_vals.append(
                        trial_balance[compute_field_list[0]] - trial_balance[compute_field_list[1]])
                elif trial_balance.subject_name_id.costs_types == 'debt' or trial_balance.subject_name_id.costs_types == 'equity':
                    subject_vals.append(
                        trial_balance[compute_field_list[1]] - trial_balance[compute_field_list[0]])
            return sum(subject_vals)

    def deal_with_balance_formula(self, balance_formula, period_id, year_begain_field):
        if balance_formula:
            return_vals = sum([self.compute_balance(one_formula, period_id, year_begain_field)
                               for one_formula in balance_formula.split(';')])
        else:
            return_vals = 0
        return return_vals

    def balance_sheet_create(self, balance_sheet_obj, year_begain_field, current_period_field):
        balance_sheet_obj.write(
            {'beginning_balance': self.deal_with_balance_formula(balance_sheet_obj.balance_formula,
                                                                      self.period_id, year_begain_field),
             'ending_balance': self.deal_with_balance_formula(balance_sheet_obj.balance_formula,
                                                                   self.period_id, current_period_field),
             'beginning_balance_two': self.deal_with_balance_formula(balance_sheet_obj.balance_two_formula,
                                                                     self.period_id, year_begain_field),
             'ending_balance_two': self.deal_with_balance_formula(balance_sheet_obj.balance_two_formula,
                                                                  self.period_id, current_period_field)})

    @api.multi
    def create_balance_sheet(self):
        """ 资产负债表的创建 """
        balance_wizard = self.env['create.trial.balance.wizard'].create(
            {'period_id': self.period_id.id})
        balance_wizard.create_trial_balance()
        view_id = self.env.ref('finance.balance_sheet_tree_wizard').id
        balance_sheet_objs = self.env['balance.sheet'].search([])
        year_begain_field = ['year_init_debit', 'year_init_credit']
        current_period_field = [
            'ending_balance_debit', 'ending_balance_credit']
        for balance_sheet_obj in balance_sheet_objs:
            self.balance_sheet_create(
                balance_sheet_obj, year_begain_field, current_period_field)
        force_company = self._context.get('force_company')
        if not force_company:
            force_company = self.env.user.company_id.id
        company_row = self.env['res.company'].browse(force_company)
        days = calendar.monthrange(
            int(self.period_id.year), int(self.period_id.month))[1]
        #TODO 格子不对 
        attachment_information = u'编制单位：' + company_row.name + u',,,,' + self.period_id.year \
                                 + u'年' + self.period_id.month + u'月' + \
                                 str(days) + u'日' + u',' + u'单位：元'
        domain = [('id', 'in', [balance_sheet_obj.id for balance_sheet_obj in balance_sheet_objs])]
        return {  # 返回生成资产负债表的数据的列表
            'type': 'ir.actions.act_window',
            'name': u'资产负债表：' + self.period_id.name,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'balance.sheet',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': self.period_id.id, 'attachment_information': attachment_information},
            'domain': domain,
            'limit': 65535,
        }

    def deal_with_profit_formula(self, occurrence_balance_formula, period_id, year_begain_field):
        if occurrence_balance_formula:
            return_vals = sum([self.compute_profit(balance_formula, period_id, year_begain_field)
                               for balance_formula in occurrence_balance_formula.split(";")
                               ])
        else:
            return_vals = 0
        return return_vals

    @api.multi
    def create_profit_statement(self):
        """生成利润表"""
        balance_wizard = self.env['create.trial.balance.wizard'].create(
            {'period_id': self.period_id.id})
        balance_wizard.create_trial_balance()
        view_id = self.env.ref('finance.profit_statement_tree').id
        balance_sheet_objs = self.env['profit.statement'].search([])
        year_begain_field = ['cumulative_occurrence_debit',
                             'cumulative_occurrence_credit']
        current_period_field = [
            'current_occurrence_debit', 'current_occurrence_credit']
        for balance_sheet_obj in balance_sheet_objs:
            balance_sheet_obj.write({'cumulative_occurrence_balance': self.deal_with_profit_formula(
                balance_sheet_obj.occurrence_balance_formula, self.period_id, year_begain_field),
                'current_occurrence_balance': self.compute_profit(
                    balance_sheet_obj.occurrence_balance_formula, self.period_id,
                    current_period_field)})
        force_company = self._context.get('force_company')
        if not force_company:
            force_company = self.env.user.company_id.id
        company_row = self.env['res.company'].browse(force_company)
        days = calendar.monthrange(
            int(self.period_id.year), int(self.period_id.month))[1]
        attachment_information = u'编制单位：' + company_row.name + u',,' + self.period_id.year \
                                 + u'年' + self.period_id.month + u'月' + u',' + u'单位：元'
        domain = [('id', 'in', [balance_sheet_obj.id for balance_sheet_obj in balance_sheet_objs])]
        return {  # 返回生成利润表的数据的列表
            'type': 'ir.actions.act_window',
            'name': u'利润表：' + self.period_id.name,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'profit.statement',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': self.period_id.id, 'attachment_information': attachment_information},
            'domain': domain,
            'limit': 65535,
        }

    @api.multi
    def compute_profit(self, parameter_str, period_id, compute_field_list):
        """ 根据传进来的 的科目的code 进行利润表的计算 """
        if parameter_str:
            parameter_str_list = parameter_str.split('~')
            subject_vals_in = []
            subject_vals_out = []
            total_sum = 0
            sign_in = False
            sign_out = False
            if len(parameter_str_list) == 1:
                subject_ids = self.env['finance.account'].search(
                    [('code', '=', parameter_str_list[0]), ('account_type', '!=', 'view')])
            else:
                subject_ids = self.env['finance.account'].search(
                    [('code', '>=', parameter_str_list[0]), ('code', '<=', parameter_str_list[1]),
                     ('account_type', '!=', 'view')])
            if subject_ids:  # 本行计算科目借贷方向
                for line in subject_ids:
                    if line.balance_directions == 'in':
                        sign_in = True
                    if line.balance_directions == 'out':
                        sign_out = True
            trial_balances = self.env['trial.balance'].search([('subject_name_id', 'in', [
                subject.id for subject in subject_ids]), ('period_id', '=', period_id.id)])
            for trial_balance in trial_balances:
                if trial_balance.subject_name_id.balance_directions == 'in':
                    subject_vals_in.append(trial_balance[compute_field_list[0]])
                elif trial_balance.subject_name_id.balance_directions == 'out':
                    subject_vals_out.append(trial_balance[compute_field_list[1]])
                if sign_out and sign_in:  # 方向有借且有贷
                    total_sum = sum(subject_vals_out) - sum(subject_vals_in)
                else:
                    if subject_vals_in:
                        total_sum = sum(subject_vals_in)
                    else:
                        total_sum = sum(subject_vals_out)
            return total_sum


class ProfitStatement(models.Model):
    """利润表模板
        模板主要用来定义项目的 科目范围,
        然后根据科目的范围得到科目范围内的科目 的利润

    """
    _name = "profit.statement"
    _order = "sequence,id"
    _description = u'利润表模板'

    sequence = fields.Integer(u'序号')

    balance = fields.Char(u'项目', help=u'报表的行次的总一个名称')
    line_num = fields.Char(u'行次', help=u'生成报表的行次')
    cumulative_occurrence_balance = fields.Float(u'本年累计金额', help=u'本年利润金额')
    occurrence_balance_formula = fields.Text(
        u'科目范围', help=u'设定本行的利润的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    current_occurrence_balance = fields.Float(u'本月金额', help=u'本月的利润的金额')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

