# -*- coding: utf-8 -*-

from odoo import models, fields, api

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
}


class buy_order(models.Model):
    _inherit = "buy.order"

    sell_id = fields.Many2one('sell.order', u'销货订单', index=True,
                              states=READONLY_STATES,
                              ondelete='restrict',
                              help=u'关联的销货订单')

    @api.multi
    def sell_to_buy(self):
        '''根据销货订单生成购货订单'''
        for order in self:
            return {
                'name': u'销货订单生成购货订单向导',
                'view_mode': 'form',
                'res_model': 'sell.to.buy.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
