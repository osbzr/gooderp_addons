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
                       sum(line.qty_remaining * (line.cost / line.goods_qty)) as cost,
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

    def _get_cost(self, warehouse=None, ignore=None):
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

            move = self.env['wh.move.line'].search(domain, limit=1, order='date desc, id desc')
            if move:
                return move.cost_unit

        return self.cost

    def get_suggested_cost_by_warehouse(
            self, warehouse, qty, lot_id=None, attribute=None, ignore_move=None):
        # 存在一种情况，计算一条line的成本的时候，先done掉该line，之后在通过该函数
        # 查询成本，此时百分百搜到当前的line，所以添加ignore参数来忽略掉指定的line
        if lot_id:
            records, cost = self.get_matching_records_by_lot(lot_id, qty, suggested=True)
        else:
            records, cost = self.get_matching_records(
                warehouse, qty, attribute=attribute, ignore_stock=True, ignore=ignore_move)

        matching_qty = sum(record.get('qty') for record in records)
        if matching_qty:
            cost_unit = safe_division(cost, matching_qty)
            if matching_qty >= qty:
                return cost, cost_unit
        else:
            cost_unit = self._get_cost(warehouse, ignore=ignore_move)
        return cost_unit * qty, cost_unit

    def is_using_matching(self):
        return True

    def is_using_batch(self):
        self.ensure_one()
        return self.using_batch

    def get_matching_records_by_lot(self, lot_id, qty, uos_qty=0, suggested=False):
        self.ensure_one()
        if not lot_id:
            raise osv.except_osv(u'错误', u'批号没有被指定，无法获得成本')

        if not suggested and lot_id.state != 'done':
            raise osv.except_osv(u'错误', u'批号%s还没有实际入库，请先审核该入库' % lot_id.move_id.name)

        if qty > lot_id.qty_remaining:
            raise osv.except_osv(u'错误', u'产品%s的库存数量不够本次出库行为' % (self.name,))

        return [{'line_in_id': lot_id.id, 'qty': qty, 'uos_qty': uos_qty}], \
            lot_id.get_real_cost_unit() * qty

    def get_matching_records(self, warehouse, qty, uos_qty=0,
                             attribute=None, ignore_stock=False, ignore=None):
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

            if attribute:
                domain.append(('attribute_id', '=', attribute.id))

            # TODO @zzx需要在大量数据的情况下评估一下速度
            lines = self.env['wh.move.line'].search(domain, order='date, id')

            qty_to_go, uos_qty_to_go, cost = qty, uos_qty, 0
            for line in lines:
                if qty_to_go <= 0 and uos_qty_to_go <= 0:
                    break

                matching_qty = min(line.qty_remaining, qty_to_go)
                matching_uos_qty = line.qty_remaining == qty_to_go and \
                    uos_qty_to_go or line.uos_qty_remaining

                matching_records.append({'line_in_id': line.id,
                                         'qty': matching_qty, 'uos_qty': matching_uos_qty})

                cost += matching_qty * line.get_real_cost_unit()
                qty_to_go -= matching_qty
                uos_qty_to_go -= matching_uos_qty
            else:
                if not ignore_stock and qty_to_go > 0:
                    raise osv.except_osv(u'错误', u'产品%s的库存数量不够本次出库行为' % (goods.name,))

            return matching_records, cost
