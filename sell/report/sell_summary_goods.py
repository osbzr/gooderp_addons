# -*- coding: utf-8 -*-

from openerp import fields, models
import datetime

class sell_summary_goods(models.Model):
    _name = 'sell.summary.goods'
    _inherit = 'report.base'
    _description = u'销售汇总表（按商品）'

    goods_categ = fields.Char(u'商品类别')
    goods_code = fields.Char(u'商品编码')
    goods = fields.Char(u'商品名称')
    attribute = fields.Char(u'属性')
    warehouse = fields.Char(u'仓库')
    uos = fields.Char(u'辅助单位')
    qty_uos = fields.Float(u'辅助数量')
    uom = fields.Char(u'基本单位')
    qty = fields.Float(u'基本数量')
    price = fields.Float(u'单价')
    amount = fields.Float(u'销售收入')
    tax_amount = fields.Float(u'税额')
    subtotal = fields.Float(u'价税合计')

    def select_sql(self, sql_type='out'):
        return '''
        SELECT MIN(wml.id) as id,
                categ.name AS goods_categ,
                goods.code AS goods_code,
                goods.name AS goods,
                attr.name AS attribute,
                wh.name AS warehouse,
                uos.name AS uos,
                SUM(wml.goods_uos_qty) AS qty_uos,
                uom.name AS uom,
                SUM(wml.goods_qty) AS qty,
                SUM(wml.amount) / SUM(wml.goods_qty) AS price,
                SUM(wml.amount) AS amount,
                SUM(wml.tax_amount) AS tax_amount,
                SUM(wml.subtotal) AS subtotal
        '''

    def from_sql(self, sql_type='out'):
        return '''
        FROM wh_move_line AS wml
            LEFT JOIN wh_move wm ON wml.move_id = wm.id
            LEFT JOIN partner ON wm.partner_id = partner.id
            LEFT JOIN goods ON wml.goods_id = goods.id
            LEFT JOIN core_category AS categ ON goods.category_id = categ.id
            LEFT JOIN attribute AS attr ON wml.attribute_id = attr.id
            LEFT JOIN warehouse AS wh ON wml.warehouse_id = wh.id
            LEFT JOIN uom AS uos ON goods.uos_id = uos.id
            LEFT JOIN uom ON goods.uom_id = uom.id
        '''

    def where_sql(self, sql_type='out'):
        extra = ''
        if self.env.context.get('partner_id'):
            extra += 'AND partner.id = {partner_id}'
        if self.env.context.get('goods_id'):
            extra += 'AND goods.id = {goods_id}'
        if self.env.context.get('goods_categ_id'):
            extra += 'AND categ.id = {goods_categ_id}'

        return '''
        WHERE wml.state = 'done'
          AND wml.date >= '{date_start}'
          AND wml.date < '{date_end}'
          AND wm.origin like 'sell.delivery%%'
          %s
        ''' % extra

    def group_sql(self, sql_type='out'):
        return '''
        GROUP BY goods_categ,goods_code,goods,attribute,warehouse,uos,uom
        '''

    def order_sql(self, sql_type='out'):
        return '''
        ORDER BY goods_code,goods,attribute,warehouse
        '''

    def get_context(self, sql_type='out', context=None):
        date_end = datetime.datetime.strptime(
            context.get('date_end'), '%Y-%m-%d') + datetime.timedelta(days=1)
        date_end = date_end.strftime('%Y-%m-%d')
        return {
            'date_start': context.get('date_start') or '',
            'date_end': date_end,
            'partner_id': context.get('partner_id') and context.get('partner_id')[0] or '',
            'goods_id': context.get('goods_id') and context.get('goods_id')[0] or '',
            'goods_categ_id': context.get('goods_categ_id') and context.get('goods_categ_id')[0] or '',
        }

    def _compute_order(self, result, order):
        order = order or 'goods_code ASC'
        return super(sell_summary_goods, self)._compute_order(result, order)

    def collect_data_by_sql(self, sql_type='out'):
        collection = self.execute_sql(sql_type='out')

        return collection

