# -*- coding: utf-8 -*-
from openerp import fields, models, api, tools


class bank_statements_report(models.Model):
    _name = "bank.statements.report"
    _description = u"现金银行报表"
    _auto = False
    _order = 'date'

    @api.one
    @api.depends('get', 'pay', 'bank_id')
    def _compute_balance(self):
        # 相邻的两条记录，bank_id不同，重新计算账户余额
        pre_record = self.search([('id', '=', self.id - 1), ('bank_id', '=', self.bank_id.id)])
        if pre_record:
            if pre_record.name != u'期初余额':
                before_balance = pre_record.balance
            else:
                before_balance = pre_record.get
        else:
            before_balance = 0
        self.balance += before_balance + self.get - self.pay

    bank_id = fields.Many2one('bank.account', string=u'账户名称', readonly=True)
    date = fields.Date(string=u'日期', readonly=True)
    name = fields.Char(string=u'单据编号', readonly=True)
    get = fields.Float(string=u'收入', readonly=True)
    pay = fields.Float(string=u'支出', readonly=True)
    balance = fields.Float(string=u'账户余额',
                           compute='_compute_balance', readonly=True)
    partner_id = fields.Many2one('partner', string=u'往来单位', readonly=True)
    note = fields.Char(string=u'备注', readonly=True)

    def init(self, cr):
        # union money_order, other_money_order, money_transfer_order
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
                (SELECT go.bank_id AS bank_id,
                        go.date AS date,
                        '期初余额' AS name,
                        go.balance AS get,
                        0 AS pay,
                        0 AS balance,
                        NULL AS partner_id,
                        NULL AS note
                FROM go_live_order AS go
                UNION ALL
                SELECT mol.bank_id,
                        mo.date,
                        mo.name,
                        (CASE WHEN mo.type = 'get' THEN mol.amount ELSE 0 END) AS get,
                        (CASE WHEN mo.type = 'pay' THEN mol.amount ELSE 0 END) AS pay,
                        0 AS balance,
                        mo.partner_id,
                        mol.note
                FROM money_order_line AS mol
                LEFT JOIN money_order AS mo ON mol.money_id = mo.id
                WHERE mo.state = 'done'
                UNION ALL
                SELECT  omo.bank_id,
                        omo.date,
                        omo.name,
                        (CASE WHEN omo.type = 'other_get' THEN omo.total_amount ELSE 0 END) AS get,
                        (CASE WHEN omo.type = 'other_pay' THEN omo.total_amount ELSE 0 END) AS pay,
                        0 AS balance,
                        omo.partner_id,
                        NULL AS note
                FROM other_money_order AS omo
                WHERE omo.state = 'done'
                UNION ALL
                SELECT  mtol.out_bank_id AS bank_id,
                        mto.date,
                        mto.name,
                        0 AS get,
                        mtol.amount AS pay,
                        0 AS balance,
                        NULL AS partner_id,
                        mto.note
                FROM money_transfer_order_line AS mtol
                LEFT JOIN money_transfer_order AS mto ON mtol.transfer_id = mto.id
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
        # 查看源单，三种情况：收付款单、其他收支单、资金转换单
        money = self.env['money.order'].search([('name', '=', self.name)])
        other_money = self.env['other.money.order'].search([('name', '=', self.name)])

        if money:
            view = self.env.ref('money.money_order_form')
            return {
                'name': u'收付款单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'money.order',
                'type': 'ir.actions.act_window',
                'res_id': money.id
            }
        elif other_money:
            view = self.env.ref('money.other_money_order_form')
            return {
                'name': u'其他收支单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'other.money.order',
                'type': 'ir.actions.act_window',
                'res_id': other_money.id,
                'context': {'type': False}
            }

        transfer_order = self.env['money.transfer.order'].search([('name', '=', self.name)])
        view = self.env.ref('money.money_transfer_order_form')

        return {
            'name': u'资金转换单',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view.id, 'form')],
            'res_model': 'money.transfer.order',
            'type': 'ir.actions.act_window',
            'res_id': transfer_order.id
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
