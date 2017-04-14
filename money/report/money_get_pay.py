# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import fields, models, api, tools

MONEY_TYPE = [
    ('pay', u'采购'),
    ('get', u'销售'),
    ('other_pay', u'其他支出'),
    ('other_get', u'其他收入'),
]


class money_get_pay_report(models.Model):
    _name = "money.get.pay.report"
    _description = u"资金收支报表"
    _auto = False
    _order = 'date'

    date = fields.Date(string=u'日期')
    name = fields.Char(string=u'单据编号')
    type = fields.Selection(MONEY_TYPE,
                            string=u'类别',
                            help=u'按类型筛选')
    partner_id = fields.Many2one('partner',
                                 string=u'往来单位')
    category_id = fields.Many2one('core.category',
                                  u'收支类别',
                                  help=u'类型：运费、咨询费等')
    amount = fields.Float(string=u'金额',
                          digits=dp.get_precision('Amount'))

    def init(self):
        # union money_order, other_money_order
        cr = self._cr
        tools.drop_view_if_exists(cr, 'money_get_pay_report')
        cr.execute("""
            CREATE or REPLACE VIEW money_get_pay_report AS (
            SELECT  ROW_NUMBER() OVER(ORDER BY name,date) AS id,
                    date,
                    name,
                    type,
                    partner_id,
                    category_id,
                    amount
            FROM
                (
                SELECT  mo.date,
                        mo.name,
                        mo.type,
                        mo.partner_id,
                        NULL AS category_id,
                        mo.amount
                FROM money_order AS mo
                WHERE mo.state = 'done'
                UNION ALL
                SELECT  omo.date,
                        omo.name,
                        omo.type,
                        omo.partner_id,
                        omol.category_id,
                        omol.amount
                FROM other_money_order AS omo
                LEFT JOIN other_money_order_line AS omol ON omo.id = omol.other_money_id
                WHERE omo.state = 'done'
                ) AS mr
            )
        """)
