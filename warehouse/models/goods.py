# -*- coding: utf-8 -*-

from utils import safe_division
from odoo.exceptions import UserError
from odoo import models, fields, api


class Goods(models.Model):
    _inherit = 'goods'

    net_weight = fields.Float(u'净重')

    # 使用SQL来取得指定商品情况下的库存数量
    def get_stock_qty(self):
        for Goods in self:
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
            ''' % (Goods.id,))

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

            move = self.env['wh.move.line'].search(
                domain, limit=1, order='cost_time desc, id desc')
            if move:
                return move.cost_unit

        return self.cost

    def get_suggested_cost_by_warehouse(
            self, warehouse, qty, lot_id=None, attribute=None, ignore_move=None):
        # 存在一种情况，计算一条line的成本的时候，先done掉该line，之后在通过该函数
        # 查询成本，此时百分百搜到当前的line，所以添加ignore参数来忽略掉指定的line
        if lot_id:
            records, cost = self.get_matching_records_by_lot(
                lot_id, qty, suggested=True)
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
        """
        是否需要获取匹配记录
        :return:
        """
        if self.no_stock:
            return False
        return True

    def is_using_batch(self):
        """
        是否使用批号管理
        :return:
        """
        self.ensure_one()
        return self.using_batch

    def get_matching_records_by_lot(self, lot_id, qty, uos_qty=0, suggested=False):
        """
        按批号来获取匹配记录
        :param lot_id: 明细中输入的批号
        :param qty: 明细中输入的数量
        :param uos_qty: 明细中输入的辅助数量
        :param suggested:
        :return: 匹配记录和成本
        """
        self.ensure_one()
        if not lot_id:
            raise UserError(u'批号没有被指定，无法获得成本')

        if not suggested and lot_id.state != 'done':
            raise UserError(u'批号%s还没有实际入库，请先审核该入库' % lot_id.move_id.name)

        if qty > lot_id.qty_remaining and not self.env.context.get('wh_in_line_ids'):
            raise UserError(u'商品%s的库存数量不够本次出库' % (self.name,))

        return [{'line_in_id': lot_id.id, 'qty': qty, 'uos_qty': uos_qty,
                 'expiration_date': lot_id.expiration_date}], \
            lot_id.get_real_cost_unit() * qty

    def get_matching_records(self, warehouse, qty, uos_qty=0,
                             attribute=None, ignore_stock=False, ignore=None):
        """
        获取匹配记录，不考虑批号
        :param ignore_stock: 当参数指定为True的时候，此时忽略库存警告
        :param ignore: 一个move_line列表，指定查询成本的时候跳过这些move
        :return: 匹配记录和成本
        """
        matching_records = []
        for Goods in self:
            domain = [
                ('qty_remaining', '>', 0),
                ('state', '=', 'done'),
                ('warehouse_dest_id', '=', warehouse.id),
                ('goods_id', '=', Goods.id)
            ]
            if ignore:
                if isinstance(ignore, (long, int)):
                    ignore = [ignore]

                domain.append(('id', 'not in', ignore))

            if attribute:
                domain.append(('attribute_id', '=', attribute.id))

            # 内部移库，从源库位移到目的库位，匹配时从源库位取值; location.py confirm_change 方法
            if self.env.context.get('location'):
                domain.append(
                    ('location_id', '=', self.env.context.get('location')))

            # TODO @zzx需要在大量数据的情况下评估一下速度
            # 出库顺序按 库位 就近、先到期先出、先进先出
            lines = self.env['wh.move.line'].search(
                domain, order='location_id, expiration_date, cost_time, id')

            qty_to_go, uos_qty_to_go, cost = qty, uos_qty, 0    # 分别为待出库商品的数量、辅助数量和成本
            for line in lines:
                if qty_to_go <= 0 and uos_qty_to_go <= 0:
                    break

                matching_qty = min(line.qty_remaining, qty_to_go)
                matching_uos_qty = matching_qty / Goods.conversion

                matching_records.append({'line_in_id': line.id, 'expiration_date': line.expiration_date,
                                         'qty': matching_qty, 'uos_qty': matching_uos_qty})

                cost += matching_qty * line.get_real_cost_unit()
                qty_to_go -= matching_qty
                uos_qty_to_go -= matching_uos_qty
            else:
                if not ignore_stock and qty_to_go > 0 and not self.env.context.get('wh_in_line_ids'):
                    raise UserError(u'商品%s的库存数量不够本次出库' % (Goods.name,))
                if self.env.context.get('wh_in_line_ids'):
                    domain = [('id', 'in', self.env.context.get('wh_in_line_ids')),
                              ('state', '=', 'done'),
                              ('warehouse_dest_id', '=', warehouse.id),
                              ('goods_id', '=', Goods.id)]
                    if attribute:
                        domain.append(('attribute_id', '=', attribute.id))
                    line_in_id = self.env['wh.move.line'].search(
                        domain, order='expiration_date, cost_time, id')
                    if line_in_id:
                        matching_records.append({'line_in_id': line_in_id.id, 'expiration_date': line_in_id.expiration_date,
                                                 'qty': qty_to_go, 'uos_qty': uos_qty_to_go})

            return matching_records, cost
