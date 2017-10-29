# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import fields, models, api


class BuyPayment(models.TransientModel):
    _name = 'buy.payment'
    _description = u'采购付款一览表'

    s_category_id = fields.Many2one('core.category', u'供应商类别')
    partner_id = fields.Many2one('partner', u'供应商')
    type = fields.Char(u'业务类别')
    date = fields.Date(u'单据日期')
    warehouse_dest_id = fields.Many2one('warehouse', u'仓库')
    order_name = fields.Char(u'单据编号')
    purchase_amount = fields.Float(u'采购金额', digits=dp.get_precision('Amount'))
    discount_amount = fields.Float(u'优惠金额', digits=dp.get_precision('Amount'))
    amount = fields.Float(u'成交金额', digits=dp.get_precision('Amount'))
    payment = fields.Float(u'已付款', digitse=dp.get_precision('Amount'))
    balance = fields.Float(u'应付款余额', digits=dp.get_precision('Amount'))
    payment_rate = fields.Float(u'付款率(%)')
    note = fields.Char(u'备注')

    @api.multi
    def view_detail(self):
        '''查看明细按钮'''
        self.ensure_one()
        order = self.env['buy.receipt'].search(
            [('name', '=', self.order_name)])
        if order:
            if not order.is_return:
                view = self.env.ref('buy.buy_receipt_form')
            else:
                view = self.env.ref('buy.buy_return_form')

            return {
                'name': u'采购入库单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'buy.receipt',
                'type': 'ir.actions.act_window',
                'res_id': order.id,
            }
