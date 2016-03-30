# -*- coding: utf-8 -*-

from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from utils import safe_division
from openerp import models, fields, api


class wh_move_matching(models.Model):
    _name = 'wh.move.matching'

    line_in_id = fields.Many2one('wh.move.line', u'出库', ondelete='set null', required=True, index=True)
    line_out_id = fields.Many2one('wh.move.line', u'入库', ondelete='set null', required=True, index=True)
    qty = fields.Float(u'数量', digits_compute=dp.get_precision('Goods Quantity'), required=True)

    def create_matching(self, line_in_id, line_out_id, qty):
        res = {
            'line_out_id': line_out_id,
            'line_in_id': line_in_id,
            'qty': qty,
        }

        return self.create(res)


class wh_move_line(models.Model):
    _inherit = 'wh.move.line'

    qty_remaining = fields.Float(compute='_get_qty_remaining', string=u'剩余数量',
        digits_compute=dp.get_precision('Goods Quantity'), index=True, store=True,readonly=True)

    matching_in_ids = fields.One2many('wh.move.matching', 'line_in_id', string=u'关联的入库')
    matching_out_ids = fields.One2many('wh.move.matching', 'line_out_id', string=u'关联的出库')

    @api.multi
    def copy(self):
        # TODO 奇怪，返回值似乎被wrapper了
        res = super(wh_move_line, self).copy()

        if res.get('warehouse_id') and res.get('warehouse_dest_id') and res.get('goods_id'):
            warehouses = self.env['warehouse'].browse([res.get('warehouse_id'),
                res.get('warehouse_dest_id')])

            if warehouses[0].type == 'stock' and warehouses[1].type != 'stock':
                goods = self.env['goods'].browse(res.get('goods_id'))
                subtotal, price = goods.get_suggested_cost_by_warehouse(warehouses[0], res.get('goods_qty'))
                res.update({'price': price, 'subtotal': subtotal})

        return res

    # 这样的function字段的使用方式需要验证一下
    @api.one
    @api.depends('goods_qty', 'matching_in_ids.qty')
    def _get_qty_remaining(self):
        self.qty_remaining = self.goods_qty - sum(match.qty for match in self.matching_in_ids)

    def get_matching_records_by_lot(self):
        for line in self:
            if line.goods_qty > line.lot_id.qty_remaining:
                raise osv.except_osv(u'错误', u'产品%s的库存数量不够本次出库行为' % (self.goods_id.name, ))

            return [{'line_in_id': line.lot_id.id, 'qty': line.goods_qty}], \
                line.lot_id.price * line.goods_qty

        return []

    def prev_action_done(self):
        matching_obj = self.env['wh.move.matching']
        for line in self:
            if line.warehouse_id.type == 'stock' and line.goods_id.is_using_matching():
                if line.goods_id.is_using_batch():
                    matching_records, subtotal = line.get_matching_records_by_lot()
                    for matching in matching_records:
                        matching_obj.create_matching(matching.get('line_in_id'),
                            line.id, matching.get('qty'))
                else:
                    matching_records, subtotal = line.goods_id.get_matching_records(
                        line.warehouse_id, line.goods_qty)

                    for matching in matching_records:
                        matching_obj.create_matching(matching.get('line_in_id'),
                            line.id, matching.get('qty'))

                line.price = safe_division(subtotal, line.goods_qty)
                line.subtotal = subtotal

        return super(wh_move_line, self).prev_action_done()

    def prev_action_cancel(self):
        for line in self:
            if line.qty_remaining != line.goods_qty:
                raise osv.except_osv(u'错误', u'当前的入库已经被其他出库匹配，请先取消相关的出库')

            line.matching_in_ids.unlink()
            line.matching_out_ids.unlink()

        return super(wh_move_line, self).prev_action_cancel()
