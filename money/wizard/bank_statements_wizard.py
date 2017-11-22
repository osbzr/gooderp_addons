# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import fields, models, api


class PartnerStatementsReportWizard(models.Model):
    _name = "bank.statements.report.wizard"
    _description = u"现金银行报表向导"

    @api.model
    def _get_company_start_date(self):
        return self._get_company_start_date_impl()

    @api.model
    def _get_company_start_date_impl(self):
        ''' 获取当前登录用户公司的启用日期 '''
        return self.env.user.company_id.start_date

    bank_id = fields.Many2one('bank.account', string=u'账户名称', required=True,
                              help=u'查看本次报表的现金/银行账户名称')
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
    def confirm_bank_statements(self):
        # 现金银行报表
        if self.from_date > self.to_date:
            raise UserError(u'结束日期不能小于开始日期！\n开始日期:%s 结束日期:%s ' %
                            (self.from_date, self.to_date))

        view = self.env.ref('money.bank_statements_report_tree')

        return {
            'name': u'现金银行报表:' + self.bank_id.name,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'bank.statements.report',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'limit': 65535,
            'type': 'ir.actions.act_window',
            'domain': [('bank_id', '=', self.bank_id.id), ('date', '>=', self.from_date), ('date', '<=', self.to_date)]
        }
