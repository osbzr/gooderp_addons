# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import fields, models, api
import datetime


class BuySummaryPartner(models.Model):
    _name = 'buy.summary.partner'
    _inherit = 'report.base'
    _description = u'采购汇总表（按供应商）'

    id_lists = fields.Text(u'移动明细行id列表')
    date = fields.Date(u'日期')
    s_category = fields.Char(u'供应商类别')
    partner = fields.Char(u'供应商')
    goods_code = fields.Char(u'商品编码')
    goods = fields.Char(u'商品名称')
    attribute = fields.Char(u'属性')
    warehouse_dest = fields.Char(u'仓库')
    qty_uos = fields.Float(u'辅助数量', digits=dp.get_precision('Quantity'))
    uos = fields.Char(u'辅助单位')
    qty = fields.Float(u'基本数量', digits=dp.get_precision('Quantity'))
    uom = fields.Char(u'基本单位')
    price = fields.Float(u'单价', digits=dp.get_precision('Price'))
    amount = fields.Float(u'采购金额', digits=dp.get_precision('Amount'))
    tax_amount = fields.Float(u'税额', digits=dp.get_precision('Amount'))
    subtotal = fields.Float(u'价税合计', digits=dp.get_precision('Amount'))

    def select_sql(self, sql_type='out'):
        return '''
        SELECT MIN(wml.id) as id,
               array_agg(wml.id) AS id_lists,
               MIN(wml.date) AS date,
               c_categ.name AS s_category,
               partner.name AS partner,
               goods.code AS goods_code,
               goods.name AS goods,
               attr.name AS attribute,
               wh.name AS warehouse_dest,
               SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.goods_uos_qty
                    ELSE - wml.goods_uos_qty END) AS qty_uos,
                uos.name AS uos,
                SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.goods_qty
                    ELSE - wml.goods_qty END) AS qty,
                uom.name AS uom,
                (CASE WHEN SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.goods_qty
                    ELSE - wml.goods_qty END) = 0 THEN 0
                ELSE
                    SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.amount
                        ELSE - wml.amount END)
                        / SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.goods_qty
                        ELSE - wml.goods_qty END)
                END) AS price,
                SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.amount
                    ELSE - wml.amount END) AS amount,
                SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.tax_amount
                    ELSE - wml.tax_amount END) AS tax_amount,
                SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.subtotal
                    ELSE - wml.subtotal END) AS subtotal
        '''

    def from_sql(self, sql_type='out'):
        return '''
        FROM wh_move_line AS wml
            LEFT JOIN wh_move wm ON wml.move_id = wm.id
            LEFT JOIN partner ON wm.partner_id = partner.id
            LEFT JOIN core_category AS c_categ
                 ON partner.s_category_id = c_categ.id
            LEFT JOIN goods ON wml.goods_id = goods.id
            LEFT JOIN attribute AS attr ON wml.attribute_id = attr.id
            LEFT JOIN warehouse AS wh ON wml.warehouse_dest_id = wh.id
                 OR wml.warehouse_id = wh.id
            LEFT JOIN uom AS uos ON goods.uos_id = uos.id
            LEFT JOIN uom ON goods.uom_id = uom.id
        '''

    def where_sql(self, sql_type='out'):
        extra = ''
        if self.env.context.get('partner_id'):
            extra += 'AND partner.id = {partner_id}'
        if self.env.context.get('goods_id'):
            extra += 'AND goods.id = {goods_id}'
        if self.env.context.get('s_category_id'):
            extra += 'AND c_categ.id = {s_category_id}'
        if self.env.context.get('warehouse_dest_id'):
            extra += 'AND wh.id = {warehouse_dest_id}'

        return '''
        WHERE wml.state = 'done'
          AND wml.date >= '{date_start}'
          AND wml.date < '{date_end}'
          AND wm.origin like 'buy%%'
          AND wh.type = 'stock'
          %s
        ''' % extra

    def order_sql(self, sql_type='out'):
        return '''
        GROUP BY s_category,partner,goods_code,goods,
                 attribute,warehouse_dest,uos,uom
        ORDER BY partner,goods_code,attribute,warehouse_dest
        '''

    def get_context(self, sql_type='out', context=None):
        date_end = datetime.datetime.strptime(
            context.get('date_end'), '%Y-%m-%d') + datetime.timedelta(days=1)
        date_end = date_end.strftime('%Y-%m-%d')
        return {
            'date_start': context.get('date_start') or '',
            'date_end': date_end,
            'partner_id': context.get('partner_id') and
            context.get('partner_id')[0] or '',
            'goods_id': context.get('goods_id') and
            context.get('goods_id')[0] or '',
            's_category_id': context.get('s_category_id') and
            context.get('s_category_id')[0] or '',
            'warehouse_dest_id': context.get('warehouse_dest_id') and
            context.get('warehouse_dest_id')[0] or '',
        }

    def _compute_order(self, result, order):
        order = order or 'partner ASC'
        return super(BuySummaryPartner, self)._compute_order(result, order)

    def collect_data_by_sql(self, sql_type='out'):
        collection = self.execute_sql(sql_type='out')

        return collection

    @api.multi
    def view_detail(self):
        '''采购汇总表（按供应商）查看明细按钮'''
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
            details = self.env['buy.order.detail'].search(
                [('order_name', '=', move_line.move_id.name),
                 ('goods_id', '=', move_line.goods_id.id)])
            for detail in details:
                res.append(detail.id)

        return {
            'name': u'采购明细表',
            'view_mode': 'tree',
            'view_id': False,
            'res_model': 'buy.order.detail',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
        }
