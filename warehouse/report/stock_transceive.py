# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api
import datetime


class ReportStockTransceive(models.Model):
    _name = 'report.stock.transceive'
    _description = u'商品收发明细表'
    _inherit = 'report.base'

    goods = fields.Char(u'商品')
    attribute = fields.Char(u'属性')
    id_lists = fields.Text(u'库存调拨id列表')
    uom = fields.Char(u'单位')
    warehouse = fields.Char(u'仓库')
    goods_qty_begain = fields.Float(
        u'期初数量', digits=dp.get_precision('Quantity'))
    cost_begain = fields.Float(
        u'期初成本', digits=dp.get_precision('Amount'))
    goods_qty_end = fields.Float(
        u'期末数量', digits=dp.get_precision('Quantity'))
    cost_end = fields.Float(
        u'期末成本', digits=dp.get_precision('Amount'))
    goods_qty_out = fields.Float(
        u'出库数量', digits=dp.get_precision('Quantity'))
    cost_out = fields.Float(
        u'出库成本', digits=dp.get_precision('Amount'))
    goods_qty_in = fields.Float(
        u'入库数量', digits=dp.get_precision('Quantity'))
    cost_in = fields.Float(
        u'入库成本', digits=dp.get_precision('Amount'))

    def select_sql(self, sql_type='out'):
        return '''
        SELECT min(line.id) as id,
                goods.name as goods,
                att.name as attribute,
                array_agg(line.id) as id_lists,
                uom.name as uom,
                wh.name as warehouse,
                sum(case when
                    line.date < '{date_start}' THEN line.goods_qty ELSE 0 END)
                    as goods_qty_begain,
                sum(case when
                    line.date < '{date_start}' THEN line.cost ELSE 0 END)
                    as cost_begain,
                sum(case when
                    line.date < '{date_end}' THEN line.goods_qty ELSE 0 END)
                    as goods_qty_end,
                sum(case when
                    line.date < '{date_end}' THEN line.cost ELSE 0 END)
                    as cost_end,
                sum(case when
                    line.date < '{date_end}' AND line.date >= '{date_start}'
                  THEN
                    line.goods_qty ELSE 0 END)
                    as goods_qty,
                sum(case when
                    line.date < '{date_end}' AND line.date >= '{date_start}'
                  THEN
                    line.cost ELSE 0 END)
                    as cost
        '''

    def from_sql(self, sql_type='out'):
        return '''
        FROM wh_move_line line
            LEFT JOIN goods goods ON line.goods_id = goods.id
            LEFT JOIN attribute att ON line.attribute_id = att.id
            LEFT JOIN uom uom ON line.uom_id = uom.id
            LEFT JOIN warehouse wh ON line.%s = wh.id
        ''' % (sql_type == 'out' and 'warehouse_id' or 'warehouse_dest_id')

    def where_sql(self, sql_type='out'):
        extra = ''
        if self.env.context.get('warehouse_id'):
            extra += 'AND wh.id = {warehouse_id}'
        if self.env.context.get('goods_id'):
            extra += 'AND goods.id = {goods_id}'
        return '''
        WHERE line.state = 'done'
          AND wh.type = 'stock'
          AND line.date < '{date_end}'
          %s
        ''' % extra

    def group_sql(self, sql_type='out'):
        return '''
        GROUP BY goods.name, att.name, uom.name, wh.name
        '''

    def order_sql(self, sql_type='out'):
        return '''
        ORDER BY goods.name, wh.name
        '''

    def get_context(self, sql_type='out', context=None):
        date_end = datetime.datetime.strptime(
            context.get('date_end'), '%Y-%m-%d') + datetime.timedelta(days=1)
        date_end = date_end.strftime('%Y-%m-%d')

        return {
            'date_start': context.get('date_start') or '',
            'date_end': date_end,
            'warehouse_id': context.get('warehouse_id') and context.get('warehouse_id')[0] or '',
            'goods_id': context.get('goods_id') and context.get('goods_id')[0] or '',
        }

    def get_record_key(self, record, sql_type='out'):
        return (
            record.get('goods'),
            record.get('uom'),
            record.get('warehouse'),
            record.get('attribute'))

    def unzip_record_key(self, key):
        return {
            'goods': key[0],
            'uom': key[1],
            'warehouse': key[2],
            'attribute': key[3],
        }

    def get_default_value_by_record(self, record, sql_type='out'):
        return {
            'id': record.get('id'),
        }

    def update_record_value(self, value, record, sql_type='out'):
        tag = sql_type == 'out' and -1 or 1

        value.update({
            'goods_qty_begain': value.get('goods_qty_begain', 0) +
                    (tag * record.get('goods_qty_begain', 0)),
            'cost_begain': value.get('cost_begain', 0) +
                    (tag * record.get('cost_begain', 0)),
            'goods_qty_end': value.get('goods_qty_end', 0) +
                    (tag * record.get('goods_qty_end', 0)),
            'cost_end': value.get('cost_end', 0) +
                    (tag * record.get('cost_end', 0)),

            'goods_qty_out': value.get('goods_qty_out', 0) +
                    (sql_type == 'out' and record.get('goods_qty', 0) or 0),
            'cost_out': value.get('cost_out', 0) +
                    (sql_type == 'out' and record.get('cost', 0) or 0),
            'goods_qty_in': value.get('goods_qty_in', 0) +
                    (sql_type == 'in' and record.get('goods_qty', 0) or 0),
            'cost_in': value.get('cost_in', 0) +
                    (sql_type == 'in' and record.get('cost', 0) or 0),
            'id_lists': value.get('id_lists', []) + record.get('id_lists', []),
        })

    def compute_history_stock_by_collect(self, res, records, sql_type='out'):
        for record in records:
            record_key = self.get_record_key(record, sql_type=sql_type)
            if not res.get(record_key):
                res[record_key] = self.get_default_value_by_record(
                    record, sql_type=sql_type)

            self.update_record_value(
                res[record_key], record, sql_type=sql_type)

    def collect_data_by_sql(self, sql_type='out'):
        out_collection = self.execute_sql(sql_type='out')
        in_collection = self.execute_sql(sql_type='in')

        res = {}
        self.compute_history_stock_by_collect(
            res, in_collection, sql_type='in')
        self.compute_history_stock_by_collect(
            res, out_collection, sql_type='out')

        result = []
        for key, value in res.iteritems():
            value.update(self.unzip_record_key(key))
            result.append(value)

        return result

    @api.multi
    def find_source_move_line(self):
        # 查看库存调拨明细
        move_line_ids = []
        # 获得'report.stock.transceive'记录集
        move_line_lists = self.get_data_from_cache(sql_type='out')

        date_start = self.env.context.get('date_start')
        date_end = self.env.context.get('date_end')
        for line in move_line_lists:
            if line.get('id') == self.id:
                domain_dict = [('date', '>=', date_start),
                               ('date', '<=', date_end),
                               ('id', 'in', line.get('id_lists'))
                               ]
                move_line_ids = [line.id for line in self.env['wh.move.line'].search(domain_dict)]

        view = self.env.ref('warehouse.wh_move_line_tree')
        return {
            'name': u'库存调拨' + date_start + u'~' + date_end,
            'view_mode': 'tree',
            'views': [(view.id, 'tree')],
            'res_model': 'wh.move.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_line_ids)]
        }
