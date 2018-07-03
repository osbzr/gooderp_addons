# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class buy_order(models.Model):
    _inherit = "buy.order"

    sell_id = fields.Many2one('sell.order', u'销货订单', index=True,
                               ondelete='restrict',
                               help=u'关联的销货订单')

    @api.multi
    def sell_to_buy(self):
        '''根据销货订单生成购货订单'''
        for order in self:
            return {
                'name': u'销货订单行',
                'view_mode': 'form',
                'view_id': False,
                'res_model': 'sell.to.buy.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new'
            }




