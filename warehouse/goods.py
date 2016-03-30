# -*- coding: utf-8 -*-

from openerp.osv import osv
from utils import safe_division

from openerp import models, fields
from openerp import api


class goods(models.Model):
    _inherit = 'goods'

    default_wh = fields.Many2one('warehouse', u'默认库位')

    # 使用SQL来取得指定产品情况下的库存数量
    def get_stock_qty(self):
        for goods in self:
            self.env.cr.execute('''
                SELECT sum(line.qty_remaining) as qty,
                       sum(line.qty_remaining * (line.subtotal / line.goods_qty)) as subtotal,
                       wh.name as warehouse
                FROM wh_move_line line
                LEFT JOIN warehouse wh ON line.warehouse_dest_id = wh.id

                WHERE line.qty_remaining > 0
                  AND wh.type = 'stock'
                  AND line.state = 'done'
                  AND line.goods_id = %s

                GROUP BY wh.name
            ''' % (goods.id, ))

            return self.env.cr.dictfetchall()

    def get_cost(self):
        # TODO 产品上需要一个字段来记录成本
        return 1

    def get_suggested_cost_by_warehouse(self, warehouse, qty):
        records, subtotal = self.get_matching_records(warehouse, qty, ignore_stock=True)

        matching_qty = sum(record.get('qty') for record in records)
        if matching_qty:
            cost = safe_division(subtotal, matching_qty)
            if matching_qty >= qty:
                return subtotal, cost
        else:
            cost = self.get_cost()
        return cost * qty, cost

    def is_using_matching(self):
        return True

    def is_using_batch(self):
        for goods in self:
            return goods.using_batch

        return False

    def get_matching_records(self, warehouse, qty, ignore_stock=False):
        matching_records = []
        for goods in self:
            domain = [
                ('qty_remaining', '>', 0),
                ('state', '=', 'done'),
                ('warehouse_dest_id', '=', warehouse.id),
                ('goods_id', '=', goods.id)
            ]

            # TODO @zzx需要在大量数据的情况下评估一下速度
            lines = self.env['wh.move.line'].search(domain, order='date, id')

            qty_to_go, subtotal = qty, 0
            for line in lines:
                if qty_to_go <= 0:
                    break

                matching_qty = min(line.qty_remaining, qty_to_go)
                matching_records.append({'line_in_id': line.id, 'qty': matching_qty})
                subtotal += matching_qty * line.get_real_price()

                qty_to_go -= matching_qty
            else:
                if not ignore_stock and qty_to_go > 0:
                    raise osv.except_osv(u'错误', u'产品%s的库存数量不够本次出库行为' % (goods.name, ))

            return matching_records, subtotal
