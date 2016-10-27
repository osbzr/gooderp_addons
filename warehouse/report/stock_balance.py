# -*- coding: utf-8 -*-

from odoo import tools
import odoo.addons.decimal_precision as dp
from odoo import models, fields


class report_stock_balance(models.Model):
    _name = 'report.stock.balance'
    _auto = False

    goods = fields.Char(u'产品')
    goods_id = fields.Many2one('goods', u'产品')
    uom = fields.Char(u'单位')
    uos = fields.Char(u'辅助单位')
    lot = fields.Char(u'批号')
    attribute_id = fields.Char(u'属性')
    warehouse = fields.Char(u'仓库')
    goods_qty = fields.Float(u'数量', digits=dp.get_precision('Quantity'))
    goods_uos_qty = fields.Float(u'辅助单位数量', digits=dp.get_precision('Quantity'))
    cost = fields.Float(u'成本', digits=dp.get_precision('Amount'))

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'report_stock_balance')
        cr.execute(
            """
            create or replace view report_stock_balance as (
                SELECT min(line.id) as id,
                       goods.name as goods,
                       goods.id as goods_id,
                       line.lot as lot,
                       attribute.name as attribute_id,
                       uom.name as uom,
                       uos.name as uos,
                       wh.name as warehouse,
                       sum(line.qty_remaining) as goods_qty,
                       sum(line.uos_qty_remaining) as goods_uos_qty,
                       sum(line.cost) as cost

                FROM wh_move_line line
                LEFT JOIN warehouse wh ON line.warehouse_dest_id = wh.id
                LEFT JOIN goods goods ON line.goods_id = goods.id
                    LEFT JOIN attribute attribute on attribute.id = line.attribute_id
                    LEFT JOIN uom uom ON goods.uom_id = uom.id
                    LEFT JOIN uom uos ON goods.uos_id = uos.id

                WHERE  wh.type = 'stock'
                  AND line.state = 'done'
                  AND ( goods.no_stock is null or goods.no_stock = FALSE)

                GROUP BY wh.name, line.lot, attribute.name, goods.name, goods.id, uom.name, uos.name

                ORDER BY goods.name, wh.name, goods_qty asc
            )
        """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
