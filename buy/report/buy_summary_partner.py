# -*- coding: utf-8 -*-

from openerp import fields, models, tools

class buy_summary_partner(models.Model):
    _name = 'buy.summary.partner'
    _auto = False
    _description = u'采购汇总表（按供应商）'

    date = fields.Date(u'日期')
    s_category = fields.Char(u'供应商类别')
    partner = fields.Char(u'供应商')
    goods_code = fields.Char(u'商品编码')
    goods = fields.Char(u'商品名称')
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

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'buy_summary_partner')
        cr.execute("""
            CREATE OR REPLACE VIEW buy_summary_partner AS (

            SELECT MIN(wml.id) AS id,
               MIN(wm.date) AS date,
               s_categ.name AS s_category,
               partner.name AS partner,
               goods.code AS goods_code,
               goods.name AS goods,
               attr.name AS attribute,
               wh.name AS warehouse_dest,
               uos.name AS uos,
               SUM(wml.goods_uos_qty) AS qty_uos,
               uom.name AS uom,
               SUM(wml.goods_qty) AS qty,
               SUM(wml.amount) / SUM(wml.goods_qty) AS price,
               SUM(wml.amount) AS amount,
               SUM(wml.tax_amount) AS tax_amount,
               SUM(wml.subtotal) AS subtotal
            
            FROM wh_move_line AS wml
            LEFT JOIN wh_move wm ON wml.move_id = wm.id
            LEFT JOIN partner ON wm.partner_id = partner.id
            LEFT JOIN core_category AS s_categ ON partner.s_category_id = s_categ.id
            LEFT JOIN goods ON wml.goods_id = goods.id
            LEFT JOIN attribute AS attr ON wml.attribute_id = attr.id
            LEFT JOIN warehouse AS wh ON wml.warehouse_dest_id = wh.id
            LEFT JOIN uom AS uos ON goods.uos_id = uos.id
            LEFT JOIN uom ON goods.uom_id = uom.id
            
            WHERE wml.state = 'done'
            AND wm.origin like 'buy%'
            GROUP BY s_category,partner,goods_code,goods,attribute,warehouse_dest,uos,uom
            ORDER BY partner,goods,attribute,warehouse_dest
            )
        """)
