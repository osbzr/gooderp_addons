# -*- coding: utf-8 -*-

from openerp.osv import osv
from utils import safe_division

from openerp import models, fields


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
            ''' % (goods.id,))

            return self.env.cr.dictfetchall()

    def get_cost(self, warehouse=None, ignore=None):
        # 如果没有历史的剩余数量，计算最后一条move的成本
        # 存在一种情况，计算一条line的成本的时候，先done掉该line，之后在通过该函数
        # 查询成本，此时百分百搜到当前的line，所以添加ignore参数来忽略掉指定的line
        self.ensure_one()
        if warehouse:
            domain = [
                ('state', '=', 'done'),
                ('goods_id', '=', self.id),
                ('warehouse_dest_id', '=', warehouse.id)
            ]

            if ignore:
                if isinstance(ignore, (long, int)):
                    ignore = [ignore]

                domain.append(('id', 'not in', ignore))

            move = self.env['wh.move.line'].search(domain, limit=1, order='date, id')
            if move:
                return move.price

        return self.cost

    def get_suggested_cost_by_warehouse(self, warehouse, qty, ignore_move=None):
        # 存在一种情况，计算一条line的成本的时候，先done掉该line，之后在通过该函数
        # 查询成本，此时百分百搜到当前的line，所以添加ignore参数来忽略掉指定的line
        records, subtotal = self.get_matching_records(warehouse, qty, ignore_stock=True,
                                                      ignore=ignore_move)

        matching_qty = sum(record.get('qty') for record in records)
        if matching_qty:
            cost = safe_division(subtotal, matching_qty)
            if matching_qty >= qty:
                return subtotal, cost
        else:
            cost = self.get_cost(warehouse, ignore=ignore_move)
        return cost * qty, cost

    def is_using_matching(self):
        return True

    def is_using_batch(self):
        for goods in self:
            return goods.using_batch

        return False

    def get_matching_records(self, warehouse, qty, uos_qty=0, ignore_stock=False, ignore=None):
        # @ignore_stock: 当参数指定为True的时候，此时忽略库存警告
        # @ignore: 一个move_line列表，指定查询成本的时候跳过这些move
        matching_records = []
        for goods in self:
            domain = [
                ('qty_remaining', '>', 0),
                ('state', '=', 'done'),
                ('warehouse_dest_id', '=', warehouse.id),
                ('goods_id', '=', goods.id)
            ]
            if ignore:
                if isinstance(ignore, (long, int)):
                    ignore = [ignore]

                domain.append(('id', 'not in', ignore))

            # TODO @zzx需要在大量数据的情况下评估一下速度
            lines = self.env['wh.move.line'].search(domain, order='date, id')

            qty_to_go, uos_qty_to_go, subtotal = qty, uos_qty, 0
            for line in lines:
                if qty_to_go <= 0 and uos_qty_to_go <= 0:
                    break

                matching_qty = min(line.qty_remaining, qty_to_go)
                matching_uos_qty = line.qty_remaining == qty_to_go and \
                    uos_qty_to_go or line.uos_qty_remaining

                matching_records.append({'line_in_id': line.id,
                                         'qty': matching_qty, 'uos_qty': matching_uos_qty})
                # subtotal += matching_qty * line.get_real_price()
                # TODO @zzx 需要考虑一下将subtotal变成计算下字段之后的影响
                subtotal += matching_qty * line.price

                qty_to_go -= matching_qty
                uos_qty_to_go -= matching_uos_qty
            else:
                if not ignore_stock and qty_to_go > 0:
                    raise osv.except_osv(u'错误', u'产品%s的库存数量不够本次出库行为' % (goods.name,))

            return matching_records, subtotal
