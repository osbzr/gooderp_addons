# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import fields, models, api


class SellOrderTrack(models.TransientModel):
    _name = 'sell.order.track'
    _description = u'销售订单跟踪表'

    goods_code = fields.Char(u'商品编码')
    goods_id = fields.Many2one('goods', u'商品名称')
    attribute = fields.Char(u'属性')
    uom = fields.Char(u'单位')
    date = fields.Date(u'订单日期')
    order_name = fields.Char(u'销售订单编号')
    user_id = fields.Many2one('res.users', u'销售员')
    partner_id = fields.Many2one('partner', u'客户')
    warehouse_id = fields.Many2one('warehouse', u'仓库')
    goods_state = fields.Char(u'状态')
    qty = fields.Float(u'数量', digits=dp.get_precision('Quantity'))
    amount = fields.Float(u'销售额', digits=dp.get_precision('Amount'))  # 商品的价税合计
    qty_not_out = fields.Float(u'未出库数量', digits=dp.get_precision('Quantity'))
    delivery_date = fields.Date(u'要求交货日期')
    wh_out_date = fields.Date(u'出库日期')
    note = fields.Char(u'备注')
    type = fields.Selection([('sell', u'销货'), ('return', u'退货')], string=u'单据类型')

    @api.multi
    def view_detail(self):
        '''查看明细按钮'''
        self.ensure_one()
        order = self.env['sell.order'].search([('name', '=', self.order_name)])
        if order:
            view = self.env.ref('sell.sell_order_form')
            return {
                'name': u'销货订单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'sell.order',
                'type': 'ir.actions.act_window',
                'res_id': order.id,
            }
