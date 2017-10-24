# -*- coding: utf-8 -*-

from odoo import tools
import odoo.addons.decimal_precision as dp
from odoo import models, fields


class ReportLotStatus(models.Model):
    _name = 'report.lot.status'
    _description = u'批次余额表'
    _auto = False

    goods = fields.Char(u'商品')
    uom = fields.Char(u'单位')
    uos = fields.Char(u'辅助单位')
    lot = fields.Char(u'批号')
    attribute_id = fields.Many2one('attribute', u'属性')
    status = fields.Char(u'状态')
    warehouse = fields.Char(u'仓库')
    date = fields.Date(u'日期')
    qty = fields.Float(u'数量', digits=dp.get_precision('Quantity'))
    uos_qty = fields.Float(u'辅助数量', digits=dp.get_precision('Quantity'))

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'report_lot_status')
        cr.execute(
            """
            create or replace view report_lot_status as (
                SELECT MIN(line.id) as id,
                        goods.name as goods,
                        uom.name as uom,
                        uos.name as uos,
                        line.lot as lot,
                        line.attribute_id as attribute_id,
                        '在库' as status,
                        wh.name as warehouse,
                        max(line.date) as date,
                        sum(line.qty_remaining) as qty,
                        sum(line.uos_qty_remaining) as uos_qty

                FROM wh_move_line line
                    LEFT JOIN goods goods ON line.goods_id = goods.id
                        LEFT JOIN uom uom ON goods.uom_id = uom.id
                        LEFT JOIN uom uos ON goods.uos_id = uos.id
                    LEFT JOIN warehouse wh ON line.warehouse_dest_id = wh.id

                WHERE line.lot IS NOT NULL
                  AND line.qty_remaining > 0
                  AND wh.type = 'stock'
                  AND line.state = 'done'

                GROUP BY goods, uom, uos, lot, attribute_id, warehouse

                ORDER BY goods, lot, warehouse
            )
        """)
