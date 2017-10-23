# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import fields, models, api


class CashFlowWizard(models.TransientModel):
    _name = "cash.flow.wizard"

    def _default_period_id_impl(self):
        """
        默认是当前会计期间
        :return: 当前会计期间的对象
        """
        return self.env['finance.period'].get_date_now_period_id()

    @api.model
    def _default_period_id(self):

        return self._default_period_id_impl()

    period_id = fields.Many2one('finance.period', string=u'会计期间',
                                default=_default_period_id)

    @api.model
    def get_amount(self, tem, report_ids, period_id):
        '''
             [('get',u'销售收款'),
              ('pay',u'采购付款'),
              ('category',u'其他收支'),
              ('begin',u'科目期初'),
              ('end',u'科目期末'),
              ('lines',u'表行计算')]
        '''
        date_start, date_end = self.env['finance.period'].get_period_month_date_range(
            period_id)
        ret = 0
        if tem.line_type == 'get' or tem.line_type == 'pay':
            # 收款单或付款单金额合计
            ret = sum([order.amount for order in self.env['money.order'].search([('type', '=', tem.line_type),
                                                                                 ('state',
                                                                                  '=', 'done'),
                                                                                 ('date', '>=',
                                                                                  date_start),
                                                                                 ('date', '<=', date_end)])])
        if tem.line_type == 'category':
            # 其他收支单金额合计
            ret = sum([line.amount for line in self.env['other.money.order.line'].search([('category_id', 'in', [c.id for c in tem.category_ids]),
                                                                                          ('other_money_id.state', '=', 'done'),
                                                                                          ('other_money_id.date', '>=', date_start),
                                                                                          ('other_money_id.date', '<=', date_end)])])
        if tem.line_type == 'begin':
            # 科目期初金额合计
            ret = sum([acc.initial_balance_debit - acc.initial_balance_credit
                       for acc in self.env['trial.balance'].search([('period_id', '=', period_id.id),
                                                                    ('subject_name_id', 'in', [b.id for b in tem.begin_ids])])])
        if tem.line_type == 'end':
            # 科目期末金额合计
            ret = sum([acc.ending_balance_debit - acc.ending_balance_credit
                       for acc in self.env['trial.balance'].search([('period_id', '=', period_id.id),
                                                                    ('subject_name_id', 'in', [e.id for e in tem.end_ids])])])
        if tem.line_type == 'lines':
            # 根据其他报表行计算
            for line in self.env['cash.flow.statement'].browse(report_ids):
                for l in tem.plus_ids:
                    if l.line_num == line.line_num:
                        ret += line.amount
                for l in tem.nega_ids:
                    if l.line_num == line.line_num:
                        ret -= line.amount
        return ret

    @api.model
    def get_year_amount(self, tem, report_ids, period_id):
        '''
             [('get',u'销售收款'),
              ('pay',u'采购付款'),
              ('category',u'其他收支'),
              ('begin',u'科目期初'),
              ('end',u'科目期末'),
              ('lines',u'表行计算')]
        '''
        date_start, date_end = self.env['finance.period'].get_period_month_date_range(
            period_id)
        date_start = date_start[0:5] + '01-01'
        ret = 0
        if tem.line_type == 'get' or tem.line_type == 'pay':
            # 收款单或付款单金额合计
            ret = sum([order.amount for order in self.env['money.order'].search([('type', '=', tem.line_type),
                                                                                 ('state',
                                                                                  '=', 'done'),
                                                                                 ('date', '>=',
                                                                                  date_start),
                                                                                 ('date', '<=', date_end)])])
        if tem.line_type == 'category':
            # 其他收支单金额合计
            ret = sum([line.amount for line in self.env['other.money.order.line'].search([('category_id', 'in', [c.id for c in tem.category_ids]),
                                                                                          ('other_money_id.state', '=', 'done'),
                                                                                          ('other_money_id.date', '>=', date_start),
                                                                                          ('other_money_id.date', '<=', date_end)])])
        if tem.line_type == 'begin':
            # 科目期初金额合计
            ret = sum([acc.year_init_debit - acc.year_init_credit
                       for acc in self.env['trial.balance'].search([('period_id', '=', period_id.id),
                                                                    ('subject_name_id', 'in', [b.id for b in tem.begin_ids])])])
        if tem.line_type == 'end':
            # 科目期末金额合计
            ret = sum([acc.ending_balance_debit - acc.ending_balance_credit
                       for acc in self.env['trial.balance'].search([('period_id', '=', period_id.id),
                                                                    ('subject_name_id', 'in', [e.id for e in tem.end_ids])])])
        if tem.line_type == 'lines':
            # 根据其他报表行计算
            for line in self.env['cash.flow.statement'].browse(report_ids):
                for l in tem.plus_ids:
                    if l.line_num == line.line_num:
                        ret += line.year_amount
                for l in tem.nega_ids:
                    if l.line_num == line.line_num:
                        ret -= line.year_amount
        return ret

    @api.multi
    def show(self):
        """生成现金流量表"""
        rep_ids = []
        '''
        old_report = self.env['cash.flow.statement'].search([('period_id','=',self.period_id.id)])
        if old_report:
            rep_ids = [rep.id for rep in old_report]
        else:
        '''
        if self.period_id:
            templates = self.env['cash.flow.template'].search([])
            for tem in templates:
                new_rep = self.env['cash.flow.statement'].create(
                    {
                        'name': tem.name,
                        'line_num': tem.line_num,
                        'amount': self.get_amount(tem, rep_ids, self.period_id),
                        'year_amount': self.get_year_amount(tem, rep_ids, self.period_id),
                    }
                )
                rep_ids.append(new_rep.id)
        view_id = self.env.ref('money.cash_flow_statement_tree').id
        attachment_information = u'编制单位：' + self.env.user.company_id.name + u',,' + self.period_id.year\
                                 + u'年' + self.period_id.month + u'月' + u',' + u'单位：元'
        return {
            'type': 'ir.actions.act_window',
            'name': u'现金流量表：' + self.period_id.name,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'cash.flow.statement',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': self.period_id.id, 'attachment_information': attachment_information},
            'domain': [('id', 'in', rep_ids)],
            'limit': 65535,
        }
