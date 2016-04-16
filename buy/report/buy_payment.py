# -*- coding: utf-8 -*-

from openerp import fields, models


class buy_payment(models.TransientModel):
    _name = 'buy.payment'
    _description = u'采购付款一览表'

    s_category_id = fields.Many2one('core.category', u'供应商类别')
    partner_id = fields.Many2one('partner', u'供应商')
    type = fields.Char(u'业务类别')
    date = fields.Date(u'单据日期')
    order_name = fields.Char(u'单据编号')
    purchase_amount = fields.Float(u'采购金额')
    discount_amount = fields.Float(u'优惠金额')
    amount = fields.Float(u'优惠后金额')
    payment = fields.Float(u'本次付款')
    balance = fields.Float(u'应付款余额')
    payment_rate = fields.Float(u'付款率(%)')
    note = fields.Char(u'备注')
