# -*- coding: utf-8 -*-

from openerp import fields, models, tools

class buy_summary_partner(models.TransientModel):
    _name = 'buy.summary.partner'
    _description = u'采购汇总表（按供应商）'

    date = fields.Date(u'日期')
    s_category_id = fields.Many2one('core.category', u'供应商类别')
    partner_id = fields.Many2one('partner', u'供应商')
    goods_code = fields.Char(u'商品编码')
    goods_id = fields.Many2one('goods', u'商品名称')
    attribute = fields.Char(u'属性')
    warehouse_dest = fields.Char(u'仓库')
    uos = fields.Char(u'辅助单位')
    qty_uos = fields.Float(u'辅助数量')
    uom = fields.Char(u'基本单位')
    qty = fields.Float(u'基本数量')
    price = fields.Float(u'单价')
    amount = fields.Float(u'采购金额')
    tax_amount = fields.Float(u'税额')
    subtotal = fields.Float(u'价税合计')

#     def init(self, cr):
#         tools.drop_view_if_exists(cr, 'buy_summary_partner')
#         cr.execute("""
#             CREATE OR REPLACE VIEW buy_summary_partner AS (
#             SELECT wml.id,
#                    wm.date,
#                    wm.partner_id as partner_id,
#                    goods.code,
#                    wml.goods_id,
#                    wml.attribute_id,
#                    wml.warehouse_dest_id,
#                    wml.uos_id,
#                    wml.goods_uos_qty,
#                    SUM(wml.goods_uos_qty) OVER (PARTITION BY wm.partner_id,wml.goods_id,wml.attribute_id,wml.warehouse_dest_id) AS 辅助数量,
#                    wml.uom_id,
#                    wml.goods_qty,
#                    SUM(wml.goods_qty) OVER (PARTITION BY wm.partner_id,wml.goods_id,wml.attribute_id,wml.warehouse_dest_id) AS 基本数量,
#                    wml.price,
#                    wml.amount,
#                    SUM(wml.amount) OVER (PARTITION BY wm.partner_id,wml.goods_id,wml.attribute_id,wml.warehouse_dest_id) AS 采购金额,
#                    wml.tax_amount,
#                    SUM(wml.tax_amount) OVER (PARTITION BY wm.partner_id,wml.goods_id,wml.attribute_id,wml.warehouse_dest_id) AS 税额,
#                    wml.subtotal,
#                    SUM(wml.subtotal) OVER (PARTITION BY wm.partner_id,wml.goods_id,wml.attribute_id,wml.warehouse_dest_id) AS 价税合计
#             FROM wh_move_line AS wml
#             LEFT JOIN goods ON wml.goods_id = goods.id
#             LEFT JOIN wh_move wm ON wml.move_id = wm.id
#             WHERE wml.state = 'done' AND wm.origin like '%buy%'
#             ORDER BY br.partner_id
#         """)