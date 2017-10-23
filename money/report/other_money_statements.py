# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import fields, models, api, tools


class OtherMoneyStatementsReport(models.Model):
    _name = "other.money.statements.report"
    _description = u"其他收支明细表"
    _auto = False

    date = fields.Date(string=u'日期', readonly=True)
    name = fields.Char(string=u'单据编号', readonly=True)
    service = fields.Many2one('service', u'收支项')
    category_id = fields.Many2one('core.category',
                                  string=u'类别', readonly=True)
    bank_id = fields.Many2one('bank.account', string='账户')
    get = fields.Float(string=u'收入', readonly=True,
                       digits=dp.get_precision('Amount'))
    pay = fields.Float(string=u'支出', readonly=True,
                       digits=dp.get_precision('Amount'))
    partner_id = fields.Many2one('partner', string=u'往来单位', readonly=True)
    note = fields.Char(string=u'备注', readonly=True)

    def init(self):
        # select other_money_order_line、other_money_order
        cr = self._cr
        tools.drop_view_if_exists(cr, 'other_money_statements_report')
        cr.execute("""
            CREATE or REPLACE VIEW other_money_statements_report AS (
            SELECT  omol.id,
                    omo.date,
                    omo.name,
                    omo.bank_id,
                    omol.service,
                    omol.category_id,
                    (CASE WHEN omo.type = 'other_get' THEN omol.amount + omol.tax_amount ELSE 0 END) AS get,
                    (CASE WHEN omo.type = 'other_pay' THEN omol.amount + omol.tax_amount ELSE 0 END) AS pay,
                    omo.partner_id,
                    omol.note
            FROM other_money_order_line AS omol
            LEFT JOIN other_money_order AS omo ON omol.other_money_id = omo.id
            WHERE omo.state = 'done'
            ORDER BY date)
        """)
