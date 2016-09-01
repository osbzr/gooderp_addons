# -*- coding: utf-8 -*-

from datetime import date
from openerp import models, fields, api
from openerp.exceptions import except_orm


class buy_order_detail_wizard(models.TransientModel):
    _name = 'buy.order.detail.wizard'
    _description = u'采购明细表向导'

    @api.model
    def _default_date_start(self):
        return self.env.user.company_id.start_date

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(u'开始日期', default=_default_date_start)
    date_end = fields.Date(u'结束日期', default=_default_date_end)
    partner_id = fields.Many2one('partner', u'供应商')
    goods_id = fields.Many2one('goods', u'商品')
    order_id = fields.Many2one('buy.receipt', u'单据编号')
    warehouse_dest_id = fields.Many2one('warehouse', u'仓库')

    @api.multi
    def button_ok(self):
        '''向导上的确定按钮'''
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        domain = [('date', '>=', self.date_start),
                  ('date', '<=', self.date_end),
                  ]

        if self.goods_id:
            domain.append(('goods_id', '=', self.goods_id.id))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        if self.order_id:
            buy_receipt = self.env['buy.receipt'].search(
                                [('id', '=', self.order_id.id)])
            domain.append(('id', '=', buy_receipt.buy_move_id.id))
        if self.warehouse_dest_id:
            domain.append(('warehouse_dest_id', '=', self.warehouse_dest_id.id))

        view = self.env.ref('buy.buy_order_detail_tree')
        return {
            'name': u'采购明细表',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'res_model': 'buy.order.detail',
            'type': 'ir.actions.act_window',
            'domain': domain,
            'limit': 300,
        }
