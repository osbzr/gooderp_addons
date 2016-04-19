# -*- coding: utf-8 -*-

import openerp.addons.decimal_precision as dp
from openerp import fields, models


class sell_receipt(models.TransientModel):
    _name = 'sell.receipt'
    _description = u'销售收款一览表'

    c_category_id = fields.Many2one('core.category', u'客户类别')
    partner_id = fields.Many2one('partner', u'客户')
    staff_id = fields.Many2one('staff', u'销售员')
    type = fields.Char(u'业务类别')
    date = fields.Date(u'单据日期')
    order_name = fields.Char(u'单据编号')
    sell_amount = fields.Float(u'销售金额', digits_compute=dp.get_precision('Amount'))
    discount_amount = fields.Float(u'优惠金额',
                                   digits_compute=dp.get_precision('Amount'))
    amount = fields.Float(u'优惠后金额', digits_compute=dp.get_precision('Amount'))
    partner_cost = fields.Float(u'客户承担费用', digits_compute=dp.get_precision('Amount'))
    receipt = fields.Float(u'本次收款', digits_compute=dp.get_precision('Amount'))
    balance = fields.Float(u'应收款余额', digits_compute=dp.get_precision('Amount'))
    receipt_rate = fields.Float(u'回款率(%)')
    note = fields.Char(u'备注')
