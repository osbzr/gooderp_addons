# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp

from odoo import fields, models, api, tools
from odoo.exceptions import UserError


class SupplierStatementsReport(models.Model):
    _inherit = "supplier.statements.report"
    _auto = False

    purchase_amount = fields.Float(string=u'采购金额', readonly=True,
                                   digits=dp.get_precision('Amount'))
    benefit_amount = fields.Float(string=u'优惠金额', readonly=True,
                                  digits=dp.get_precision('Amount'))
    move_id = fields.Many2one('wh.move', string=u'出入库单', readonly=True)

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
                    purchase_amount,
                    benefit_amount,
                    amount,
                    pay_amount,
                    discount_money,
                    balance_amount,
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
                ) AS ps)
        """)

    @api.multi
    def find_source_order(self):
        # 查看原始单据，三情况：收付款单、采购退货单、采购入库单、核销单
        self.ensure_one()
        model_view = {
            'money.order': {'name': u'付款单',
                            'view': 'money.money_order_form'},
            'buy.receipt': {'name': u'采购入库单',
                            'view': 'buy.buy_receipt_form',
                            'name_return': u'采购退货单',
                            'view_return': 'buy.buy_return_form'},
            'reconcile.order': {'name': u'核销单',
                                'view': 'money.reconcile_order_form'}
        }
        for model, view_dict in model_view.iteritems():
            res = self.env[model].search([('name', '=', self.name)])
            name = model == 'buy.receipt' and res.is_return and \
                view_dict['name_return'] or view_dict['name']
            view = model == 'buy.receipt' and res.is_return and \
                self.env.ref(view_dict['view_return']) \
                or self.env.ref(view_dict['view'])
            if res:
                return {
                    'name': name,
                    'view_mode': 'form',
                    'view_id': False,
                    'views': [(view.id, 'form')],
                    'res_model': model,
                    'type': 'ir.actions.act_window',
                    'res_id': res.id,
                }
        raise UserError(u'期初余额没有原始单据可供查看。')


class SupplierStatementsReportWithGoods(models.TransientModel):
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
        # 三情况：收付款单、采购退货单、采购入库单、核销单
        self.ensure_one()
        model_view = {
            'money.order': {'name': u'付款单',
                            'view': 'money.money_order_form'},
            'buy.receipt': {'name': u'采购入库单',
                            'view': 'buy.buy_receipt_form',
                            'name_return': u'采购退货单',
                            'view_return': 'buy.buy_return_form'},
            'reconcile.order': {'name': u'核销单',
                                'view': 'money.reconcile_order_form'}
        }
        for model, view_dict in model_view.iteritems():
            res = self.env[model].search([('name', '=', self.name)])
            name = model == 'buy.receipt' and res.is_return and \
                view_dict['name_return'] or view_dict['name']
            view = model == 'buy.receipt' and res.is_return and \
                self.env.ref(view_dict['view_return']) \
                or self.env.ref(view_dict['view'])
            if res:
                return {
                    'name': name,
                    'view_mode': 'form',
                    'view_id': False,
                    'views': [(view.id, 'form')],
                    'res_model': model,
                    'type': 'ir.actions.act_window',
                    'res_id': res.id,
                }
        raise UserError(u'期初余额没有原始单据可供查看。')
