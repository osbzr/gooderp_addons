# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import fields, models, api, tools


class BankStatementsReport(models.Model):
    _name = "bank.statements.report"
    _description = u"现金银行报表"
    _auto = False
    _order = 'date'

    @api.one
    @api.depends('get', 'pay', 'bank_id')
    def _compute_balance(self):
        # 相邻的两条记录，bank_id不同，重新计算账户余额
        pre_record = self.search(
            [('id', '<=', self.id), ('bank_id', '=', self.bank_id.id)])
        for pre in pre_record:
            self.balance += pre.get - pre.pay

    bank_id = fields.Many2one('bank.account', string=u'账户名称', readonly=True)
    date = fields.Date(string=u'日期', readonly=True)
    name = fields.Char(string=u'单据编号', readonly=True)
    get = fields.Float(string=u'收入', readonly=True,
                       digits=dp.get_precision('Amount'))
    pay = fields.Float(string=u'支出', readonly=True,
                       digits=dp.get_precision('Amount'))
    balance = fields.Float(string=u'账户余额',
                           compute='_compute_balance', readonly=True,
                           digits=dp.get_precision('Amount'))
    partner_id = fields.Many2one('partner', string=u'往来单位', readonly=True)
    note = fields.Char(string=u'备注', readonly=True)

    def init(self):
        # union money_order, other_money_order, money_transfer_order
        cr = self._cr
        tools.drop_view_if_exists(cr, 'bank_statements_report')
        cr.execute("""
            CREATE or REPLACE VIEW bank_statements_report AS (
            SELECT  ROW_NUMBER() OVER(ORDER BY bank_id,date) AS id,
                    bank_id,
                    date,
                    name,
                    get,
                    pay,
                    balance,
                    partner_id,
                    note
            FROM
                (
                SELECT mol.bank_id,
                        mo.date,
                        mo.name,
                        (CASE WHEN mo.type = 'get' THEN mol.amount ELSE 0 END) AS get,
                        (CASE WHEN mo.type = 'pay' THEN mol.amount ELSE 0 END) AS pay,
                        0 AS balance,
                        mo.partner_id,
                        mo.note
                FROM money_order_line AS mol
                LEFT JOIN money_order AS mo ON mol.money_id = mo.id
                WHERE mo.state = 'done'
                UNION ALL
                SELECT  omo.bank_id,
                        omo.date,
                        omo.name,
                        (CASE WHEN omo.type = 'other_get' THEN
                         (CASE WHEN ba.currency_id IS NULL THEN omo.total_amount ELSE omo.currency_amount END)
                         ELSE 0 END) AS get,
                        (CASE WHEN omo.type = 'other_pay' THEN
                         (CASE WHEN ba.currency_id IS NULL THEN omo.total_amount ELSE omo.currency_amount END)
                         ELSE 0 END) AS pay,
                        0 AS balance,
                        omo.partner_id,
                        omo.note AS note
                FROM other_money_order AS omo
                LEFT JOIN bank_account AS ba ON ba.id = omo.bank_id
                LEFT JOIN res_currency AS rc ON rc.id = ba.currency_id
                WHERE omo.state = 'done'
                UNION ALL
                SELECT  mtol.out_bank_id AS bank_id,
                        mto.date,
                        mto.name,
                        0 AS get,
                        (CASE WHEN ba.currency_id IS NULL THEN mtol.amount ELSE mtol.currency_amount END) AS pay,
                        0 AS balance,
                        NULL AS partner_id,
                        mto.note
                FROM money_transfer_order_line AS mtol
                LEFT JOIN money_transfer_order AS mto ON mtol.transfer_id = mto.id
                LEFT JOIN bank_account AS ba ON ba.id = mtol.out_bank_id
                LEFT JOIN res_currency AS rc ON rc.id = ba.currency_id
                WHERE mto.state = 'done'
                UNION ALL
                SELECT  mtol.in_bank_id AS bank_id,
                        mto.date,
                        mto.name,
                        mtol.amount AS get,
                        0 AS pay,
                        0 AS balance,
                        NULL AS partner_id,
                        mto.note
                FROM money_transfer_order_line AS mtol
                LEFT JOIN money_transfer_order AS mto ON mtol.transfer_id = mto.id
                WHERE mto.state = 'done'
                ) AS bs)
        """)

    @api.multi
    def find_source_order(self):
        # 查看原始单据，三种情况：收付款单、其他收支单、资金转换单
        self.ensure_one()
        model_view = {
            'money.order': {'name': u'收付款单',
                            'view': 'money.money_order_form'},
            'other.money.order': {'name': u'其他收支单',
                                  'view': 'money.other_money_order_form'},
            'money.transfer.order': {'name': u'资金转换单',
                                     'view': 'money.money_transfer_order_form'}}
        for model, view_dict in model_view.iteritems():
            res = self.env[model].search([('name', '=', self.name)])
            name = view_dict['name']
            view = self.env.ref(view_dict['view'])
            if res:
                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': False,
                    'views': [(view.id, 'form')],
                    'res_model': model,
                    'type': 'ir.actions.act_window',
                    'res_id': res.id
                }
