# -*- coding: utf-8 -*-

from odoo import fields, models, api
import odoo.addons.decimal_precision as dp
import datetime


class SellTopTen(models.Model):
    _name = 'sell.top.ten'
    _inherit = 'report.base'
    _description = u'销量前十商品'

    goods = fields.Char(u'商品名称')
    warehouse = fields.Char(u'仓库')
    qty = fields.Float(u'基本数量', digits=dp.get_precision('Quantity'))
    amount = fields.Float(u'销售收入', digits=dp.get_precision('Amount'))

    def select_sql(self, sql_type='out'):
        return '''
        SELECT MIN(wml.id) as id,
                goods.name AS goods,
                wh.name AS warehouse,
                (SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_qty
                    ELSE 0 END) -
                    SUM(CASE WHEN wm.origin = 'sell.delivery.return' THEN wml.goods_qty
                    ELSE 0 END)) AS qty,
                (SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.amount
                    ELSE 0 END) -
                    SUM(CASE WHEN wm.origin = 'sell.delivery.return' THEN wml.amount
                    ELSE 0 END)) AS amount
        '''

    def from_sql(self, sql_type='out'):
        return '''
        FROM wh_move_line AS wml
            LEFT JOIN wh_move wm ON wml.move_id = wm.id
            LEFT JOIN goods ON wml.goods_id = goods.id
            LEFT JOIN warehouse AS wh ON wml.warehouse_id = wh.id
        '''

    def where_sql(self, sql_type='out'):
        extra = ''
        if self.env.context.get('warehouse_id'):
            extra += 'AND wh.id = {warehouse_id}'
        return '''
        WHERE wml.state = 'done'
          AND wml.date >= '{date_start}'
          AND wml.date < '{date_end}'
          AND wm.origin like 'sell.delivery%%'
          AND wh.type = 'stock'
          %s
        ''' % extra

    def group_sql(self, sql_type='out'):
        return '''
        GROUP BY goods, warehouse
        '''

    def order_sql(self, sql_type='out'):
        return '''
        ORDER BY qty DESC
        fetch first 10 rows only
        '''

    def get_context(self, sql_type='out', context=None):
        date_end = datetime.datetime.strptime(
            context.get('date_end'), '%Y-%m-%d') + datetime.timedelta(days=1)
        date_end = date_end.strftime('%Y-%m-%d')
        return {
            'date_start': context.get('date_start') or '',
            'date_end': date_end,
            'warehouse_id': context.get('warehouse_id') and
            context.get('warehouse_id')[0] or '',
        }

    def collect_data_by_sql(self, sql_type='out'):
        collection = self.execute_sql(sql_type='out')

        return collection
