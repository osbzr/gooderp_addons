# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import fields, models, api


class OtherMoneyStatementsReportWizard(models.Model):
    _name = "other.money.statements.report.wizard"
    _description = u"其他收支明细表向导"

    @api.model
    def _get_company_start_date(self):
        return self._get_company_start_date_impl()

    @api.model
    def _get_company_start_date_impl(self):
        ''' 获取当前登录用户公司的启用日期 '''
        return self.env.user.company_id.start_date

    from_date = fields.Date(string=u'开始日期', required=True, default=_get_company_start_date,
                            help=u'查看本次报表的开始日期')  # 默认公司启用日期
    to_date = fields.Date(string=u'结束日期', required=True,
                          default=lambda self: fields.Date.context_today(self),
                          help=u'查看本次报表的结束日期')  # 默认当前日期
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def confirm_other_money_statements(self):
        """
        其他收支明细表
        :return: action
        """
        self.ensure_one()
        if self.from_date > self.to_date:
            raise UserError(u'结束日期不能小于开始日期。')

        view = self.env.ref('money.other_money_statements_report_tree')

        return {
            'name': u'其他收支明细表',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'other.money.statements.report',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'limit': 65535,
            'type': 'ir.actions.act_window',
            'domain': [('date', '>=', self.from_date), ('date', '<=', self.to_date)]
        }
