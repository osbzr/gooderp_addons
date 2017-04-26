# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import fields, models, api, tools


class supplier_statements_report(models.Model):
    _name = "supplier.statements.report"
    _description = u"供应商对账单"
    _auto = False
    _order = 'id, date'

    @api.one
    @api.depends('amount', 'pay_amount', 'partner_id')
    def _compute_balance_amount(self):
        pre_record = self.search([
            ('id', '=', self.id - 1),
            ('partner_id', '=', self.partner_id.id)
        ])
        # 相邻的两条记录，partner不同，应付款余额要清零并重新计算
        if pre_record:
            before_balance = pre_record.balance_amount
        else:
            before_balance = 0
        self.balance_amount += before_balance + self.amount - self.pay_amount + self.discount_money

    partner_id = fields.Many2one('partner', string=u'业务伙伴', readonly=True)
    name = fields.Char(string=u'单据编号', readonly=True)
    date = fields.Date(string=u'单据日期', readonly=True)
    done_date = fields.Datetime(string=u'完成日期', readonly=True)
    amount = fields.Float(string=u'应付金额', readonly=True,
                          digits=dp.get_precision('Amount'))
    pay_amount = fields.Float(string=u'实际付款金额', readonly=True,
                              digits=dp.get_precision('Amount'))
    discount_money = fields.Float(string=u'付款折扣', readonly=True,
                                  digits=dp.get_precision('Amount'))
    balance_amount = fields.Float(
        string=u'应付款余额',
        compute='_compute_balance_amount',
        readonly=True,
        digits=dp.get_precision('Amount'))
    note = fields.Char(string=u'备注', readonly=True)

    def init(self):
        # union money_order(type = 'pay'), money_invoice(type = 'expense')
        cr = self._cr
        tools.drop_view_if_exists(cr, 'supplier_statements_report')
        cr.execute("""
            CREATE or REPLACE VIEW supplier_statements_report AS (
            SELECT  ROW_NUMBER() OVER(ORDER BY partner_id, date, amount desc) AS id,
                    partner_id,
                    name,
                    date,
                    done_date,
                    amount,
                    pay_amount,
                    discount_money,
                    balance_amount,
                    note
            FROM
                (
                SELECT m.partner_id,
                        m.name,
                        m.date,
                        m.write_date AS done_date,
                        0 AS amount,
                        m.amount AS pay_amount,
                        m.discount_amount AS discount_money,
                        0 AS balance_amount,
                        m.note
                FROM money_order AS m
                WHERE m.type = 'pay' AND m.state = 'done'
                UNION ALL
                SELECT  mi.partner_id,
                        mi.name,
                        mi.date,
                        mi.create_date AS done_date,
                        mi.amount,
                        0 AS pay_amount,
                        0 AS discount_money,
                        0 AS balance_amount,
                        Null AS note
                FROM money_invoice AS mi
                LEFT JOIN core_category AS c ON mi.category_id = c.id
                WHERE c.type = 'expense' AND mi.state = 'done'
                UNION ALL
                SELECT  ro.partner_id,
                        ro.name,
                        ro.date,
                        ro.write_date AS done_date,
                        0 AS amount,
                        sol.this_reconcile AS pay_amount,
                        0 AS discount_money,
                        0 AS balance_amount,
                        Null AS note
                FROM reconcile_order AS ro
                LEFT JOIN money_invoice AS mi ON mi.name = ro.name
                LEFT JOIN source_order_line AS sol ON sol.payable_reconcile_id = ro.id
                WHERE ro.state = 'done' AND mi.state = 'done' AND mi.name ilike 'RO%'
                ) AS ps)
        """)
