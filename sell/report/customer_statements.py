# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import fields, models, api, tools

class customer_statements_report(models.Model):
    _name = "customer.statements.report"
    _description = u"客户对账单"
    _auto = False
    _order = 'date'

    @api.one
    @api.depends('amount', 'pay_amount', 'partner_id')
    def _compute_balance_amount(self):
        pre_record = self.search([('id', '=', self.id - 1), ('partner_id', '=', self.partner_id.id)])
        # 相邻的两条记录，partner不同，应收款余额重新计算
        if pre_record:
            before_balance = pre_record.balance_amount
        else:
            before_balance = 0
        self.balance_amount += before_balance + self.amount - self.pay_amount

    partner_id = fields.Many2one('partner', string=u'业务伙伴', readonly=True)
    name = fields.Char(string=u'单据编号', readonly=True)
    date = fields.Date(string=u'单据日期', readonly=True)
    sale_amount = fields.Float(string=u'销售金额', readonly=True)
    benefit_amount = fields.Float(string=u'优惠金额', readonly=True)
    fee = fields.Float(string=u'客户承担费用', readonly=True)
    amount = fields.Float(string=u'应收金额', readonly=True)
    pay_amount = fields.Float(string=u'付款金额', readonly=True)
    balance_amount = fields.Float(string=u'应收款余额', compute='_compute_balance_amount', readonly=True)
    note = fields.Char(string=u'备注', readonly=True)
    move_id = fields.Many2one('wh.move', string=u'出入库单', readonly=True)

    def init(self, cr):
        # union money_order(type = 'get'), money_invoice(type = 'income')
        tools.drop_view_if_exists(cr, 'customer_statements_report')
        cr.execute("""
            CREATE or REPLACE VIEW customer_statements_report AS (
            SELECT  ROW_NUMBER() OVER(ORDER BY partner_id,date) AS id,
                    partner_id,
                    name,
                    date,
                    sale_amount,
                    benefit_amount,
                    fee,
                    amount,
                    pay_amount,
                    balance_amount,
                    note,
                    move_id
            FROM
                (SELECT m.partner_id,
                        m.name,
                        m.date,
                        0 AS sale_amount,
                        0 AS benefit_amount,
                        0 AS fee,
                        0 AS amount,
                        m.amount AS pay_amount,
                        0 AS balance_amount,
                        m.note,
                        NULL AS move_id
                FROM money_order AS m
                WHERE m.type = 'get'
                UNION ALL
                SELECT  mi.partner_id,
                        mi.name,
                        mi.date,
                        sd.amount + sd.discount_amount AS sale_amount,
                        sd.discount_amount AS benefit_amount,
                        sd.partner_cost AS fee,
                        mi.amount,
                        0 AS pay_amount,
                        0 AS balance_amount,
                        Null AS note,
                        mi.move_id
                FROM money_invoice AS mi
                LEFT JOIN core_category AS c ON mi.category_id = c.id
                JOIN sell_delivery AS sd ON sd.sell_move_id = mi.move_id
                WHERE c.type = 'income'
                ) AS ps)
        """)

    @api.multi
    def find_source_order(self):
        # 查看源单，两种情况：收款单、销售发货单
        money = self.env['money.order'].search([('name', '=', self.name)])
        # 收款单
        if money:
            view = self.env.ref('money.money_order_form')
            return {
                'name': u'收款单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'money.order',
                'type': 'ir.actions.act_window',
                'res_id': money.id,
                'context': {'type': 'get'}
            }

        # 销售发货单
        delivery = self.env['sell.delivery'].search([('name', '=', self.name)])
        view = self.env.ref('sell.sell_delivery_form')

        return {
            'name': u'销售发货单',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view.id, 'form')],
            'res_model': 'sell.delivery',
            'type': 'ir.actions.act_window',
            'res_id': delivery.id,
            'context': {'type': 'get'}
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
