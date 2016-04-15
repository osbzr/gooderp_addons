# -*- coding: utf-8 -*-

import openerp.addons.decimal_precision as dp
from openerp import models, fields


class report_stock_transceive_collect(models.Model):
    _name = 'report.stock.transceive.collect'
    _inherit = 'report.stock.transceive'

    ORIGIN_MAP = {
        ('wh.internal', True): 'internal_out',
        ('wh.internal', False): 'internal_in',

        'wh.out.others': 'others_out',
        'wh.in.others': 'others_in',
        'wh.out.losses': 'losses_out',
        'wh.in.overage': 'overage_in',

        'buy.receipt.buy': u'purchase_in',
        'buy.receipt.return': u'purchase_out',
        'sell.delivery.sell': u'sale_out',
        'sell.delivery.return': u'sale_in',

        ('wh.assembly', True): 'assembly_out',
        ('wh.assembly', False): 'assembly_in',

        ('wh.disassembly', True): 'disassembly_out',
        ('wh.disassembly', False): 'disassembly_in',
    }

    NEED_TUPLE_ORIGIN_MAP = ['wh.internal', 'wh.assembly', 'wh.disassembly']

    internal_in_qty = fields.Float(u'调拨入库数量', digits_compute=dp.get_precision('Goods Quantity'))
    internal_in_cost = fields.Float(u'调拨入库成本', digits_compute=dp.get_precision('Accounting'))

    purchase_in_qty = fields.Float(u'普通采购数量', digits_compute=dp.get_precision('Goods Quantity'))
    purchase_in_cost = fields.Float(u'普通采购成本', digits_compute=dp.get_precision('Accounting'))

    sale_in_qty = fields.Float(u'销售退回数量', digits_compute=dp.get_precision('Goods Quantity'))
    sale_in_cost = fields.Float(u'销售退回成本', digits_compute=dp.get_precision('Accounting'))

    others_in_qty = fields.Float(u'其他入库数量', digits_compute=dp.get_precision('Goods Quantity'))
    others_in_cost = fields.Float(u'其他入库成本', digits_compute=dp.get_precision('Accounting'))

    overage_in_qty = fields.Float(u'盘盈数量', digits_compute=dp.get_precision('Goods Quantity'))
    overage_in_cost = fields.Float(u'盘盈成本', digits_compute=dp.get_precision('Accounting'))

    assembly_in_qty = fields.Float(u'组装单入库数量', digits_compute=dp.get_precision('Goods Quantity'))
    assembly_in_cost = fields.Float(u'组装单入库成本', digits_compute=dp.get_precision('Accounting'))

    disassembly_in_qty = fields.Float(u'拆卸单入库数量', digits_compute=dp.get_precision('Goods Quantity'))
    disassembly_in_cost = fields.Float(u'拆卸单入库成本', digits_compute=dp.get_precision('Accounting'))

    internal_out_qty = fields.Float(u'调拨出库数量', digits_compute=dp.get_precision('Goods Quantity'))
    internal_out_cost = fields.Float(u'调拨出库成本', digits_compute=dp.get_precision('Accounting'))

    purchase_out_qty = fields.Float(u'采购退回数量', digits_compute=dp.get_precision('Goods Quantity'))
    purchase_out_cost = fields.Float(u'采购退回成本', digits_compute=dp.get_precision('Accounting'))

    sale_out_qty = fields.Float(u'普通销售购量', digits_compute=dp.get_precision('Goods Quantity'))
    sale_out_cost = fields.Float(u'普通销售购本', digits_compute=dp.get_precision('Accounting'))

    others_out_qty = fields.Float(u'其他出库数量', digits_compute=dp.get_precision('Goods Quantity'))
    others_out_cost = fields.Float(u'其他出库成本', digits_compute=dp.get_precision('Accounting'))

    losses_out_qty = fields.Float(u'盘亏数量', digits_compute=dp.get_precision('Goods Quantity'))
    losses_out_cost = fields.Float(u'盘亏成本', digits_compute=dp.get_precision('Accounting'))

    assembly_out_qty = fields.Float(u'组装单出库数量', digits_compute=dp.get_precision('Goods Quantity'))
    assembly_out_cost = fields.Float(u'组装单出库成本', digits_compute=dp.get_precision('Accounting'))

    disassembly_out_qty = fields.Float(u'拆卸单出库数量', digits_compute=dp.get_precision('Goods Quantity'))
    disassembly_out_cost = fields.Float(u'拆卸单出库成本', digits_compute=dp.get_precision('Accounting'))

    def compute_specific_data(self, res):
        line_obj = self.env['wh.move.line']
        for result in res:
            for line in line_obj.browse(result.get('lines')):
                if line.move_id.origin in self.NEED_TUPLE_ORIGIN_MAP:
                    origin = self.ORIGIN_MAP.get((line.move_id.origin, result.get('warehouse') == line.warehouse_id.name))
                else:
                    origin = self.ORIGIN_MAP.get(line.move_id.origin)

                if not result.get(origin + '_qty'):
                    result[origin + '_qty'] = 0
                    result[origin + '_cost'] = 0

                result[origin + '_qty'] += line.goods_qty
                result[origin + '_cost'] += line.cost

    def select_sql(self, sql_type='out'):
        select = super(report_stock_transceive_collect, self).select_sql(sql_type=sql_type)
        select += ', array_agg(line.id) as lines'

        return select

    def collect_data_by_sql(self, sql_type='out'):
        res = super(report_stock_transceive_collect, self).collect_data_by_sql(sql_type=sql_type)
        self.compute_specific_data(res)

        return res

    def update_record_value(self, value, record, sql_type='out'):
        super(report_stock_transceive_collect, self).update_record_value(value, record, sql_type=sql_type)
        value.update({
                'lines': value.get('lines', []) + record.get('lines', ''),
            })
