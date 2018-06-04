# -*- coding: utf-8 -*-

from odoo import tools
import odoo.addons.decimal_precision as dp
from odoo import models, fields


class ReportSellSummary(models.Model):
    _name = 'report.sell.summary'
    _description = u'销售汇总表'
    _auto = False

    partner_id = fields.Many2one('partner', u'客户')
    department_id = fields.Many2one('staff.department', u'部门')
    user_id = fields.Many2one('res.users', u'销售员')
    goods = fields.Char(u'商品名')
    goods_id = fields.Many2one('goods', u'商品')
    brand_id = fields.Many2one('core.value', u'品牌')
    location = fields.Char(u'库位')
    uom = fields.Char(u'单位')
    uos = fields.Char(u'辅助单位')
    lot = fields.Char(u'批号')
    attribute_id = fields.Char(u'属性')
    warehouse = fields.Char(u'仓库')
    goods_qty = fields.Float(u'数量', digits=dp.get_precision('Quantity'))
    goods_uos_qty = fields.Float(
        u'辅助单位数量', digits=dp.get_precision('Quantity'))
    price = fields.Float(u'单价', digits=dp.get_precision('Price'))
    amount = fields.Float(u'销售收入', digits=dp.get_precision('Amount'))
    tax_amount = fields.Float(u'税额', digits=dp.get_precision('Amount'))
    subtotal = fields.Float(u'价税合计', digits=dp.get_precision('Amount'))
    margin = fields.Float(u'毛利', digits=dp.get_precision('Amount'))
    date = fields.Date(u'日期')
    last_receipt_date = fields.Date(string=u'最后收款日期')

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'report_sell_summary')
        cr.execute(
            """
            create or replace view report_sell_summary as (
                SELECT min(wml.id) AS id,
                    wm.partner_id AS partner_id,
                    wm.user_id AS user_id,
                    staff.department_id AS department_id,
                    goods.name AS goods,
                    goods.id AS goods_id,
                    goods.brand AS brand_id,
                    loc.name AS location,
                    wml.lot AS lot,
                    attribute.name AS attribute_id,
                    uom.name AS uom,
                    uos.name AS uos,
                    wh.name AS warehouse,
                    wm.date AS date,
                    SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_uos_qty
                           ELSE - wml.goods_uos_qty END) AS goods_uos_qty,
                    SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_qty
                        ELSE - wml.goods_qty END) AS goods_qty,
                    (CASE WHEN SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_qty
                                        ELSE - wml.goods_qty END) = 0 THEN 0
                        ELSE SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.amount
                                    ELSE - wml.amount END)
                            / SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_qty
                                    ELSE - wml.goods_qty END)
                    END) AS price,
                    SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.amount
                            ELSE - wml.amount END) AS amount,
                    SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.tax_amount
                            ELSE - wml.tax_amount END) AS tax_amount,
                    SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.subtotal
                            ELSE - wml.subtotal END) AS subtotal,
                    (SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.amount
                            ELSE - wml.amount END) - SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_qty
                                                            ELSE - wml.goods_qty END) * wml.cost_unit) AS margin,
                    mi.get_amount_date AS last_receipt_date

                FROM wh_move_line wml
                LEFT JOIN wh_move wm ON wml.move_id = wm.id
                    LEFT JOIN res_users ru ON wm.user_id = ru.id
                        LEFT JOIN staff ON staff.user_id = ru.id
                LEFT JOIN warehouse wh ON wml.warehouse_dest_id = wh.id OR wml.warehouse_id = wh.id
                LEFT JOIN goods goods ON wml.goods_id = goods.id
                    LEFT JOIN uom uom ON goods.uom_id = uom.id
                    LEFT JOIN uom uos ON goods.uos_id = uos.id
                LEFT JOIN attribute attribute on attribute.id = wml.attribute_id
                LEFT JOIN location loc ON loc.goods_id = wml.goods_id
                LEFT JOIN sell_delivery AS sd ON wm.id = sd.sell_move_id
                LEFT JOIN money_invoice AS mi ON mi.id = sd.invoice_id

                WHERE wh.type = 'stock'
                  AND wml.state = 'done'
                  AND wm.origin like 'sell.delivery%%'
                  AND (goods.no_stock is null or goods.no_stock = FALSE)

                GROUP BY wm.partner_id, wm.user_id, staff.department_id, goods.name, goods.id, goods.brand, loc.name, wml.lot, attribute.name, uom.name, uos.name, wh.name, wml.cost_unit,wm.date,
                 mi.get_amount_date

                ORDER BY goods.name, wh.name, goods_qty asc
            )
        """)
