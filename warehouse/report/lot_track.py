# -*- coding: utf-8 -*-

import openerp.addons.decimal_precision as dp
from openerp import models, fields
import datetime


class report_lot_track(models.Model):
    _name = 'report.lot.track'
    _inherit = 'report.base'

    goods = fields.Char(u'产品')
    uom = fields.Char(u'单位')
    uos = fields.Char(u'辅助单位')
    lot = fields.Char(u'批号')
    attribute_id = fields.Many2one('attribute', u'属性')
    warehouse = fields.Char(u'仓库')
    date = fields.Date(u'日期')
    uos_qty = fields.Float(u'辅助数量', digits_compute=dp.get_precision('Goods Quantity'))
    qty = fields.Float(u'数量', digits_compute=dp.get_precision('Goods Quantity'))
    origin = fields.Char(u'业务类型')

    def compute_origin(self, results):
        line_obj = self.env['wh.move.line']
        for result in results:
            line = line_obj.browse(result.get('id'))
            result.update({
                'origin': line.with_context(internal_out=result.get('type') == 'out').get_origin_explain()
            })

    def select_sql(self, sql_type='out'):
        return '''
        SELECT line.id as id,
                goods.name as goods,
                uom.name as uom,
                uos.name as uos,
                %s.lot as lot,
                line.attribute_id as attribute_id,
                '%s' as type,
                wh.name as warehouse,
                line.date as date,
                line.goods_qty as qty,
                line.goods_uos_qty as uos_qty
        ''' % (sql_type == 'out' and 'lot' or 'line', sql_type)

    def from_sql(self, sql_type='out'):
        if sql_type == 'out':
            warehouse = 'warehouse_id'
            extra = 'LEFT JOIN wh_move_line lot ON line.lot_id = lot.id'
        else:
            warehouse, extra = 'warehouse_dest_id', ''

        return '''
        FROM wh_move_line line
            LEFT JOIN goods goods ON line.goods_id = goods.id
                LEFT JOIN uom uom ON goods.uom_id = uom.id
                LEFT JOIN uom uos ON goods.uos_id = uos.id
            LEFT JOIN warehouse wh ON line.{warehouse} = wh.id
            {extra}
        '''.format(warehouse=warehouse, extra=extra)

    def where_sql(self, sql_type='out'):
        return '''
        WHERE line.state = 'done'
          AND line.%s IS NOT NULL
          AND wh.type = 'stock'
          AND line.date >= '{date_start}'
          AND line.date < '{date_end}'
          AND wh.name ilike '%%{warehouse}%%'
          AND goods.name ilike '%%{goods}%%'
        ''' % (sql_type == 'out' and 'lot_id' or 'lot')

    def order_sql(self, sql_type='out'):
        return '''
        ORDER BY lot, date, goods, warehouse
        '''

    def get_context(self, sql_type='out', context=None):
        date_end = datetime.datetime.strptime(
            context.get('date_end'), '%Y-%m-%d') + datetime.timedelta(days=1)
        date_end = date_end.strftime('%Y-%m-%d')

        return {
            'date_start': context.get('date_start') or '',
            'date_end': date_end,
            'warehouse': context.get('warehouse') or '',
            'goods': context.get('goods') or '',
        }

    def _compute_order(self, result, order):
        order = order or 'goods DESC'
        return super(report_lot_track, self)._compute_order(result, order)

    def collect_data_by_sql(self, sql_type='out'):
        out_collection = self.execute_sql(sql_type='out')
        in_collection = self.execute_sql(sql_type='in')

        result = out_collection + in_collection
        self.compute_origin(result)

        return result
