# -*- coding: utf-8 -*-
from openerp.exceptions import except_orm
from openerp import fields, models, api

class partner_statements_report_wizard(models.Model):
    _name = "bank.statements.report.wizard"
    _description = u"现金银行报表向导"

    @api.model
    def _get_company_start_date(self):
        return self.env.user.company_id.start_date

    bank_id = fields.Many2one('bank.account', string=u'账户名称', required=True)
    from_date = fields.Date(string=u'开始日期', required=True, default=_get_company_start_date) # 默认公司启用日期
    to_date = fields.Date(string=u'结束日期', required=True, default=lambda self: fields.Date.context_today(self)) # 默认当前日期

    @api.multi
    def confirm_bank_statements(self):
        # 现金银行报表
        if self.from_date > self.to_date:
            raise except_orm(u'错误！', u'结束日期不能小于开始日期！')

        view = self.env.ref('money.bank_statements_report_tree')

        return {
                'name': u'现金银行报表:' + self.bank_id.name,
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'bank.statements.report',
                'view_id': False,
                'views': [(view.id, 'tree')],
                'type': 'ir.actions.act_window',
                'domain':[('bank_id','=', self.bank_id.id), ('date','>=', self.from_date), ('date','<=', self.to_date)]
                }
