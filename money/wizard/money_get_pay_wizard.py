# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import fields, models, api

MONEY_TYPE = [
    ('pay', u'采购'),
    ('get', u'销售'),
    ('other_pay', u'其他支出'),
    ('other_get', u'其他收入'),
]


class MoneyGetPayWizard(models.Model):
    _name = "money.get.pay.wizard"
    _description = u"资金收支报表向导"

    @api.model
    def _get_company_start_date(self):
        return self._get_company_start_date_impl()

    @api.model
    def _get_company_start_date_impl(self):
        ''' 获取当前登录用户公司的启用日期 '''
        return self.env.user.company_id.start_date

    type = fields.Selection(MONEY_TYPE,
                            string=u'类别',
                            help=u'按类型筛选')
    date_start = fields.Date(string=u'开始日期',
                             required=True,
                             default=_get_company_start_date,
                             help=u'查看本次报表的开始日期')  # 默认公司启用日期
    date_end = fields.Date(string=u'结束日期',
                           required=True,
                           default=lambda self: fields.Date.context_today(
                               self),
                           help=u'查看本次报表的结束日期')  # 默认当前日期
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def button_confirm(self):
        """资金收支报表"""
        if self.date_start > self.date_end:
            raise UserError(u'结束日期不能小于开始日期\n开始日期:%s 结束日期:%s ' %
                            (self.date_start, self.date_end))

        view = self.env.ref('money.money_get_pay_report_tree')
        domain = [('date', '>=', self.date_start),
                  ('date', '<=', self.date_end)]
        if self.type:
            domain.append(('type', '=', self.type))

        return {
            'name': u'资金收支报表',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'money.get.pay.report',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'limit': 65535,
            'type': 'ir.actions.act_window',
            'domain': domain,
            'context': {'search_default_group_date': 1,
                        'search_default_group_partner': 1,
                        'search_default_group_category_id': 1}
        }
