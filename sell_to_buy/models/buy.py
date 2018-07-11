# -*- coding: utf-8 -*-

from odoo import models, fields, api


class buy_order(models.Model):
    _inherit = "buy.order"

    sell_id = fields.Many2one('sell.order', u'销货订单', index=True,
                              readonly=True,
                              copy=False,
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


class buy_order_line(models.Model):
    _inherit = "buy.order.line"

    sell_line_id = fields.Many2one('sell.order.line',
                                   u'销货单行',
                                   copy=False,
                                   ondelete='restrict',
                                   help=u'对应的销货订单行')

    @api.multi
    def unlink(self):
        '''删除购货订单行时，如果对应销货订单行已采购，则去掉打勾'''
        for line in self:
            if line.sell_line_id:
                line.sell_line_id.is_bought = False
        return super(buy_order_line, self).unlink()
