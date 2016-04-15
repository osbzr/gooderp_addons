# -*- coding: utf-8 -*-

from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp import models, fields


class report_stock_balance(models.Model):
    _name = 'report.stock.balance'
    _auto = False

    goods = fields.Char(u'产品')
    uom = fields.Char(u'单位')
    uos = fields.Char(u'辅助单位')
    lot = fields.Char(u'批号')
    attribute_id = fields.Many2one('attribute', u'属性')
    warehouse = fields.Char(u'仓库')
    goods_qty = fields.Float('数量', digits_compute=dp.get_precision('Goods Quantity'))
    goods_uos_qty = fields.Float('辅助单位数量', digits_compute=dp.get_precision('Goods Quantity'))
    cost = fields.Float(u'成本', digits_compute=dp.get_precision('Accounting'))

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_balance')
        cr.execute(
            """
            create or replace view report_stock_balance as (
                SELECT min(line.id) as id,
                       goods.name as goods,
                       line.lot as lot,
                       line.attribute_id as attribute_id,
                       uom.name as uom,
                       uos.name as uos,
                       wh.name as warehouse,
                       sum(line.qty_remaining) as goods_qty,
                       sum(line.uos_qty_remaining) as goods_uos_qty,
                       sum(line.cost) as cost

                FROM wh_move_line line
                LEFT JOIN warehouse wh ON line.warehouse_dest_id = wh.id
                LEFT JOIN goods goods ON line.goods_id = goods.id
                    LEFT JOIN uom uom ON goods.uom_id = uom.id
                    LEFT JOIN uom uos ON goods.uos_id = uos.id

                WHERE line.qty_remaining > 0
                  AND wh.type = 'stock'
                  AND line.state = 'done'

                GROUP BY wh.name, line.lot, line.attribute_id, goods.name, uom.name, uos.name

                ORDER BY goods.name, wh.name, goods_qty asc
            )
        """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
