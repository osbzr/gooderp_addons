# -*- coding: utf-8 -*-

from openerp import fields, models, api, tools


class other_money_statements_report(models.Model):
    _name = "other.money.statements.report"
    _description = u"其他收支明细表"
    _auto = False

    date = fields.Date(string=u'日期', readonly=True)
    name = fields.Char(string=u'单据编号', readonly=True)
    type = fields.Char(string=u'类别', readonly=True)
    category_id = fields.Many2one('core.category',
                                  string=u'收支项目', readonly=True)
    get = fields.Float(string=u'收入', readonly=True)
    pay = fields.Float(string=u'支出', readonly=True)
    partner_id = fields.Many2one('partner', string=u'往来单位', readonly=True)
    note = fields.Char(string=u'备注', readonly=True)

    def init(self, cr):
        # select other_money_order_line、other_money_order
        tools.drop_view_if_exists(cr, 'other_money_statements_report')
        cr.execute("""
            CREATE or REPLACE VIEW other_money_statements_report AS (
            SELECT  omol.id,
                    omo.date,
                    omo.name,
                    (CASE WHEN omo.type = 'other_get' THEN '其他收入' ELSE '其他支出' END) AS type,
                    omol.category_id,
                    (CASE WHEN omo.type = 'other_get' THEN omol.amount ELSE 0 END) AS get,
                    (CASE WHEN omo.type = 'other_pay' THEN omol.amount ELSE 0 END) AS pay,
                    omo.partner_id,
                    omol.note
            FROM other_money_order_line AS omol
            LEFT JOIN other_money_order AS omo ON omol.other_money_id = omo.id
            WHERE omo.state = 'done'
            ORDER BY date)
        """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
