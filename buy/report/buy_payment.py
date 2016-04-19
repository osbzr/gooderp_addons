# -*- coding: utf-8 -*-

import openerp.addons.decimal_precision as dp
from openerp import fields, models


class buy_payment(models.TransientModel):
    _name = 'buy.payment'
    _description = u'采购付款一览表'

    s_category_id = fields.Many2one('core.category', u'供应商类别')
    partner_id = fields.Many2one('partner', u'供应商')
    type = fields.Char(u'业务类别')
    date = fields.Date(u'单据日期')
    order_name = fields.Char(u'单据编号')
    purchase_amount = fields.Float(u'采购金额', digits_compute=dp.get_precision('Amount'))
    discount_amount = fields.Float(u'优惠金额', digits_compute=dp.get_precision('Amount'))
    amount = fields.Float(u'优惠后金额', digits_compute=dp.get_precision('Amount'))
    payment = fields.Float(u'本次付款', digits_compute=dp.get_precision('Amount'))
    balance = fields.Float(u'应付款余额', digits_compute=dp.get_precision('Amount'))
    payment_rate = fields.Float(u'付款率(%)')
    note = fields.Char(u'备注')
