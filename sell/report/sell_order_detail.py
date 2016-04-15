# -*- coding: utf-8 -*-

from openerp import fields, models

class sell_order_detail(models.TransientModel):
    _name = 'sell.order.detail'
    _description = u'销售明细表'

    date = fields.Date(u'销售日期')
    order_name = fields.Char(u'销售单据号')
    type = fields.Char(u'业务类型')
    staff_id = fields.Many2one('staff', u'销售员')
    partner_id = fields.Many2one('partner', u'客户')
    goods_code = fields.Char(u'商品编码')
    goods_id = fields.Many2one('goods', u'商品名称')
    attribute = fields.Char(u'属性')
    uom = fields.Char(u'单位')
    warehouse_dest = fields.Char(u'仓库')
    qty = fields.Float(u'数量')
    price = fields.Float(u'单价')
    amount = fields.Float(u'销售收入')
    tax_amount = fields.Float(u'税额')
    subtotal = fields.Float(u'价税合计')
    note = fields.Char(u'备注')
