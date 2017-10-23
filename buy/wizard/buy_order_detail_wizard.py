# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class BuyOrderDetailWizard(models.TransientModel):
    _name = 'buy.order.detail.wizard'
    _description = u'采购明细表向导'

    @api.model
    def _default_date_start(self):
        return self.env.user.company_id.start_date

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(u'开始日期', default=_default_date_start,
                             help=u'报表汇总的开始日期，默认为公司启用日期')
    date_end = fields.Date(u'结束日期', default=_default_date_end,
                           help=u'报表汇总的结束日期，默认为当前日期')
    partner_id = fields.Many2one('partner', u'供应商',
                                 help=u'按指定供应商进行统计')
    goods_id = fields.Many2one('goods', u'商品',
                               help=u'按指定商品进行统计')
    order_id = fields.Many2one('buy.receipt', u'单据编号',
                               help=u'按指定单据编号进行统计')
    warehouse_dest_id = fields.Many2one('warehouse', u'仓库',
                                        help=u'按指定仓库进行统计')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def button_ok(self):
        '''向导上的确定按钮'''
        self.ensure_one()
        if self.date_end < self.date_start:
            raise UserError(u'开始日期不能大于结束日期！')

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
            domain.append(('warehouse_dest_id', '=',
                           self.warehouse_dest_id.id))

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
            'limit': 65535,
        }
