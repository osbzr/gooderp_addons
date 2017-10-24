# -*- coding: utf-8 -*-

from odoo import fields, models, api
import odoo.addons.decimal_precision as dp
import datetime


class SellSummaryGoods(models.Model):
    _name = 'sell.summary.goods'
    _inherit = 'report.base'
    _description = u'销售汇总表（按商品）'

    id_lists = fields.Text(u'移动明细行id列表')
    goods_categ = fields.Char(u'商品类别')
    goods_code = fields.Char(u'商品编码')
    goods = fields.Char(u'商品名称')
    attribute = fields.Char(u'属性')
    warehouse = fields.Char(u'仓库')
    qty_uos = fields.Float(u'辅助数量', digits=dp.get_precision('Quantity'))
    uos = fields.Char(u'辅助单位')
    qty = fields.Float(u'基本数量', digits=dp.get_precision('Quantity'))
    uom = fields.Char(u'基本单位')
    price = fields.Float(u'单价', digits=dp.get_precision('Price'))
    amount = fields.Float(u'销售收入', digits=dp.get_precision('Amount'))
    tax_amount = fields.Float(u'税额', digits=dp.get_precision('Amount'))
    subtotal = fields.Float(u'价税合计', digits=dp.get_precision('Amount'))
    margin = fields.Float(u'毛利', digits=dp.get_precision('Amount'))

    def select_sql(self, sql_type='out'):
        return '''
        SELECT MIN(wml.id) as id,
                array_agg(wml.id) AS id_lists,
                categ.name AS goods_categ,
                goods.code AS goods_code,
                goods.name AS goods,
                attr.name AS attribute,
                wh.name AS warehouse,
                SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_uos_qty
                    ELSE - wml.goods_uos_qty END) AS qty_uos,
                uos.name AS uos,
                SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_qty
                    ELSE - wml.goods_qty END) AS qty,
                uom.name AS uom,
                (CASE WHEN SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_qty
                    ELSE - wml.goods_qty END) = 0 THEN 0
                ELSE
                    SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.amount
                        ELSE - wml.amount END)
                        / SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_qty
                        ELSE - wml.goods_qty END)
                END) AS price,
                SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.amount
                    ELSE - wml.amount END) AS amount,
                SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.tax_amount
                    ELSE - wml.tax_amount END) AS tax_amount,
                SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.subtotal
                    ELSE - wml.subtotal END) AS subtotal,
                (SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.amount
                    ELSE - wml.amount END) - SUM(CASE WHEN wm.origin = 'sell.delivery.sell' THEN wml.goods_qty
                    ELSE - wml.goods_qty END) * wml.cost_unit) AS margin
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
                 OR wml.warehouse_dest_id = wh.id
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
        GROUP BY goods_categ,goods_code,goods,attribute,warehouse,uos,uom,wml.cost_unit
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
            'warehouse_id': context.get('warehouse_id') and context.get('warehouse_id')[0] or '',
        }

    def _compute_order(self, result, order):
        order = order or 'goods_code ASC'
        return super(SellSummaryGoods, self)._compute_order(result, order)

    def collect_data_by_sql(self, sql_type='out'):
        collection = self.execute_sql(sql_type='out')

        return collection

    @api.multi
    def view_detail(self):
        '''销售汇总表（按商品）查看明细按钮'''
        self.ensure_one()
        line_ids = []
        res = []
        move_lines = []
        result = self.get_data_from_cache()
        for line in result:
            if line.get('id') == self.id:
                line_ids = line.get('id_lists')
                move_lines = self.env['wh.move.line'].search(
                    [('id', 'in', line_ids)])

        for move_line in move_lines:
            details = self.env['sell.order.detail'].search(
                [('order_name', '=', move_line.move_id.name),
                 ('goods_id', '=', move_line.goods_id.id)])
            for detail in details:
                res.append(detail.id)

        return {
            'name': u'销售明细表',
            'view_mode': 'tree',
            'view_id': False,
            'res_model': 'sell.order.detail',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
        }
