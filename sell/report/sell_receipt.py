# -*- coding: utf-8 -*-

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
    sell_amount = fields.Float(u'销售金额')
    discount_amount = fields.Float(u'优惠金额')
    amount = fields.Float(u'优惠后金额')
    partner_cost = fields.Float(u'客户承担费用')
    receipt = fields.Float(u'本次收款')
    balance = fields.Float(u'应收款余额')
    receipt_rate = fields.Float(u'回款率(%)')
    note = fields.Char(u'备注')
