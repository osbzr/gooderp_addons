# -*- coding: utf-8 -*-

from openerp import models, fields, api


class popup_wizard(models.TransientModel):
    _name = 'popup.wizard'
    _description = u'发货单缺货向导'
    
    msg = fields.Text(u'消息', default= lambda self: self.env.context.get('msg'),
                      help=u'发货单缺货信息')

    @api.one
    def button_ok(self):
        method = self.env.context.get('method')
        vals = self.env.context.get('vals')
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if method == 'goods_inventery':
            self.goods_inventery(vals, active_model, active_id)
    
    @api.one
    def goods_inventery(self, vals, active_model, active_id):
        auto_in = self.env['wh.in'].create(vals)
        auto_in.approve_order()
        self.env[active_model].browse(active_id).sell_delivery_done()



