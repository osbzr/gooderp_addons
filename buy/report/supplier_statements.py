# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp

from odoo import fields, models, api, tools
from odoo.exceptions import UserError


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
            before_balance = pre_record.this_balance_amount
        else:
            before_balance = 0
        self.balance_amount += before_balance + self.amount - self.pay_amount + self.discount_money
        self.this_balance_amount = self.balance_amount

    partner_id = fields.Many2one('partner', string=u'业务伙伴', readonly=True)
    name = fields.Char(string=u'单据编号', readonly=True)
    date = fields.Date(string=u'单据日期', readonly=True)
    done_date = fields.Datetime(string=u'完成日期', readonly=True)
    purchase_amount = fields.Float(string=u'采购金额', readonly=True,
                                   digits=dp.get_precision('Amount'))
    benefit_amount = fields.Float(string=u'优惠金额', readonly=True,
                                  digits=dp.get_precision('Amount'))
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
    this_balance_amount = fields.Float(string=u'应付款余额',
                                       digits=dp.get_precision('Amount'))
    note = fields.Char(string=u'备注', readonly=True)
    move_id = fields.Many2one('wh.move', string=u'出入库单', readonly=True)

    def init(self):
        # union money_order(type = 'pay'), money_invoice(type = 'expense')
        cr = self._cr
        tools.drop_view_if_exists(cr, 'supplier_statements_report')
        cr.execute("""
            CREATE or REPLACE VIEW supplier_statements_report AS (
            SELECT  ROW_NUMBER() OVER(ORDER BY partner_id) AS id,
                    partner_id,
                    name,
                    date,
                    done_date,
                    purchase_amount,
                    benefit_amount,
                    amount,
                    pay_amount,
                    discount_money,
                    balance_amount,
                    0 AS this_balance_amount,
                    note,
                    move_id
            FROM
                (
                SELECT m.partner_id,
                        m.name,
                        m.date,
                        m.write_date AS done_date,
                        0 AS purchase_amount,
                        0 AS benefit_amount,
                        0 AS amount,
                        m.amount AS pay_amount,
                        m.discount_amount AS discount_money,
                        0 AS balance_amount,
                        m.note,
                        NULL AS move_id
                FROM money_order AS m
                WHERE m.type = 'pay' AND m.state = 'done'
                UNION ALL
                SELECT  mi.partner_id,
                        mi.name,
                        mi.date,
                        mi.create_date AS done_date,
                        br.amount + br.discount_amount AS purchase_amount,
                        br.discount_amount AS benefit_amount,
                        mi.amount,
                        0 AS pay_amount,
                        0 AS discount_money,
                        0 AS balance_amount,
                        Null AS note,
                        mi.move_id
                FROM money_invoice AS mi
                LEFT JOIN core_category AS c ON mi.category_id = c.id
                LEFT JOIN buy_receipt AS br ON br.buy_move_id = mi.move_id
                WHERE c.type = 'expense' AND mi.state = 'done'
                UNION ALL
                SELECT  ro.partner_id,
                        ro.name,
                        ro.date,
                        ro.write_date AS done_date,
                        0 AS purchase_amount,
                        0 AS benefit_amount,
                        0 AS amount,
                        sol.this_reconcile AS pay_amount,
                        0 AS discount_money,
                        0 AS balance_amount,
                        Null AS note,
                        0 AS move_id
                FROM reconcile_order AS ro
                LEFT JOIN money_invoice AS mi ON mi.name = ro.name
                LEFT JOIN source_order_line AS sol ON sol.payable_reconcile_id = ro.id
                WHERE ro.state = 'done' AND mi.state = 'done' AND mi.name ilike 'RO%'
                ) AS ps)
        """)

    @api.multi
    def find_source_order(self):
        # 查看原始单据，三情况：收付款单、采购退货单、采购入库单
        self.ensure_one()
        money = self.env['money.order'].search([('name', '=', self.name)])
        # 付款单
        if money:
            view = self.env.ref('money.money_order_form')
            return {
                'name': u'付款单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'money.order',
                'type': 'ir.actions.act_window',
                'res_id': money.id,
                'context': {'type': 'pay'}
            }

        # 采购退货单、入库单
        buy = self.env['buy.receipt'].search([('name', '=', self.name)])
        if buy:
            if buy.is_return:
                view = self.env.ref('buy.buy_return_form')
                return {
                    'name': u'采购退货单',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': False,
                    'views': [(view.id, 'form')],
                    'res_model': 'buy.receipt',
                    'type': 'ir.actions.act_window',
                    'res_id': buy.id,
                    'context': {'type': 'pay'}
                }
            else:
                view = self.env.ref('buy.buy_receipt_form')
                return {
                    'name': u'采购入库单',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': False,
                    'views': [(view.id, 'form')],
                    'res_model': 'buy.receipt',
                    'type': 'ir.actions.act_window',
                    'res_id': buy.id,
                    'context': {'type': 'pay'}
                }
        raise UserError(u'期初余额没有原始单据可供查看！')


class supplier_statements_report_with_goods(models.TransientModel):
    _name = "supplier.statements.report.with.goods"
    _description = u"供应商对账单带商品明细"

    partner_id = fields.Many2one('partner', string=u'业务伙伴', readonly=True)
    name = fields.Char(string=u'单据编号', readonly=True)
    date = fields.Date(string=u'单据日期', readonly=True)
    done_date = fields.Date(string=u'完成日期', readonly=True)
    category_id = fields.Many2one('core.category', u'商品类别')
    goods_code = fields.Char(u'商品编号')
    goods_name = fields.Char(u'商品名称')
    attribute_id = fields.Many2one('attribute', u'规格型号')
    uom_id = fields.Many2one('uom', u'单位')
    quantity = fields.Float(u'数量',
                            digits=dp.get_precision('Quantity'))
    price = fields.Float(u'单价',
                         digits=dp.get_precision('Amount'))
    discount_amount = fields.Float(u'折扣额',
                                   digits=dp.get_precision('Amount'))
    without_tax_amount = fields.Float(u'不含税金额',
                                      digits=dp.get_precision('Amount'))
    tax_amount = fields.Float(u'税额',
                              digits=dp.get_precision('Amount'))
    order_amount = fields.Float(string=u'采购金额', readonly=True,
                                digits=dp.get_precision('Amount'))  # 采购
    benefit_amount = fields.Float(string=u'优惠金额', readonly=True,
                                  digits=dp.get_precision('Amount'))
    fee = fields.Float(string=u'客户承担费用', readonly=True,
                       digits=dp.get_precision('Amount'))
    amount = fields.Float(string=u'应付金额', readonly=True,
                          digits=dp.get_precision('Amount'))
    pay_amount = fields.Float(string=u'实际付款金额', readonly=True,
                              digits=dp.get_precision('Amount'))
    discount_money = fields.Float(string=u'付款折扣', readonly=True,
                                  digits=dp.get_precision('Amount'))
    balance_amount = fields.Float(string=u'应付款余额', readonly=True,
                                  digits=dp.get_precision('Amount'))
    note = fields.Char(string=u'备注', readonly=True)
    move_id = fields.Many2one('wh.move', string=u'出入库单', readonly=True)

    @api.multi
    def find_source_order(self):
        # 三情况：收付款单、采购退货单、采购入库单
        self.ensure_one()
        money = self.env['money.order'].search([('name', '=', self.name)])
        if money:  # 付款单
            view = self.env.ref('money.money_order_form')
            return {
                'name': u'付款单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'money.order',
                'type': 'ir.actions.act_window',
                'res_id': money.id,
                'context': {'type': 'pay'}
            }

        # 采购退货单、入库单
        buy = self.env['buy.receipt'].search([('name', '=', self.name)])
        if buy:
            if buy.is_return:
                view = self.env.ref('buy.buy_return_form')
                return {
                    'name': u'采购退货单',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': False,
                    'views': [(view.id, 'form')],
                    'res_model': 'buy.receipt',
                    'type': 'ir.actions.act_window',
                    'res_id': buy.id,
                    'context': {'type': 'pay'}
                }
            else:
                view = self.env.ref('buy.buy_receipt_form')
                return {
                    'name': u'采购入库单',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': False,
                    'views': [(view.id, 'form')],
                    'res_model': 'buy.receipt',
                    'type': 'ir.actions.act_window',
                    'res_id': buy.id,
                    'context': {'type': 'pay'}
                }

        raise UserError(u'期初余额没有原始单据可供查看！')
