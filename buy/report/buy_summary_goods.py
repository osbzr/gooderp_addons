# -*- coding: utf-8 -*-

from openerp import fields, models

class buy_summary_goods(models.TransientModel):
    _name = 'buy.summary.goods'
    _description = u'采购汇总表（按商品）'

#     order_name = fields.Char(u'采购订单号')
    goods_categ_id = fields.Many2one('core.category', u'商品类别')
    goods_code = fields.Char(u'商品编码')
    goods_id = fields.Many2one('goods', u'商品名称')
    attribute = fields.Char(u'属性')
    warehouse_dest = fields.Char(u'仓库')
    uos = fields.Char(u'辅助单位')
    qty_uos = fields.Float(u'辅助数量')
    uom = fields.Char(u'基本单位')
    qty = fields.Float(u'基本数量')
    price = fields.Float(u'单价')
    amount = fields.Float(u'采购金额')
    tax_amount = fields.Float(u'税额')
    subtotal = fields.Float(u'价税合计')
