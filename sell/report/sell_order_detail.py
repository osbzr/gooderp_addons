# -*- coding: utf-8 -*-

import openerp.addons.decimal_precision as dp
from openerp import fields, models, api

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
    warehouse = fields.Char(u'仓库')
    qty = fields.Float(u'数量', digits_compute=dp.get_precision('Quantity'))
    price = fields.Float(u'单价', digits_compute=dp.get_precision('Amount'))
    amount = fields.Float(u'销售收入', digits_compute=dp.get_precision('Amount'))
    tax_amount = fields.Float(u'税额', digits_compute=dp.get_precision('Amount'))
    subtotal = fields.Float(u'价税合计', digits_compute=dp.get_precision('Amount'))
    note = fields.Char(u'备注')

    @api.multi
    def view_detail(self):
        '''查看明细按钮'''
        order = self.env['sell.delivery'].search([('name', '=', self.order_name)])
        if order:
            if not order.is_return:
                view = self.env.ref('sell.sell_delivery_form')
            else:
                view = self.env.ref('sell.sell_return_form')
            
            return {
                'name': u'销售发货单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'sell.delivery',
                'type': 'ir.actions.act_window',
                'res_id': order.id,
            }
