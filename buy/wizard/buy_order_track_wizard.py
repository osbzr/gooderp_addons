# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class BuyOrderTrackWizard(models.TransientModel):
    _name = 'buy.order.track.wizard'
    _description = u'采购订单跟踪表向导'

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
                                 help=u'只统计选定的供应商')
    goods_id = fields.Many2one('goods', u'商品',
                               help=u'只统计选定的商品')
    order_id = fields.Many2one('buy.order', u'订单号',
                               help=u'只统计选定的订单号')
    warehouse_dest_id = fields.Many2one('warehouse', u'仓库',
                                        help=u'只统计选定的仓库')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    def _get_domain(self):
        '''返回wizard界面上条件'''
        domain = [
            ('order_id.date', '>=', self.date_start),
            ('order_id.date', '<=', self.date_end)
        ]
        if self.goods_id:
            domain.append(('goods_id', '=', self.goods_id.id))
        if self.partner_id:
            domain.append(('order_id.partner_id', '=', self.partner_id.id))
        if self.order_id:
            domain.append(('order_id.id', '=', self.order_id.id))
        if self.warehouse_dest_id:
            domain.append(('order_id.warehouse_dest_id',
                           '=', self.warehouse_dest_id.id))
        return domain

    def _get_wh_in_date(self, line):
        '''对于一个buy order line，返回一个入库日期'''
        wh_in_date = None
        move_line = self.env['wh.move.line']
        wh_move_line = move_line.search([
            ('buy_line_id', '=', line.id),
            ('state', '=', 'done')
        ])
        if len(wh_move_line) > 1:  # 如果是分批入库，则入库单明细行上的buy_line_id相同
            wh_in_date = wh_move_line[0].date
        else:
            wh_in_date = wh_move_line.date
        return wh_in_date

    def _prepare_track_line(self, line, qty, amount, qty_not_in):
        '''返回跟踪表明细行（非小计行）'''
        return {
            'goods_code': line.goods_id.code,
            'goods_id': line.goods_id.id,
            'attribute': line.attribute_id.name,
            'uom': line.uom_id.name,
            'date': line.order_id.date,
            'order_name': line.order_id.name,
            'partner_id': line.order_id.partner_id.id,
            'warehouse_dest_id': line.order_id.warehouse_dest_id.id,
            'goods_state': line.order_id.goods_state,
            'qty': qty,
            'amount': amount,
            'qty_not_in': qty_not_in,
            'planned_date': line.order_id.planned_date,
            'wh_in_date': self._get_wh_in_date(line),  # 入库日期
            'note': line.note,
            'type': line.order_id.type,
        }

    @api.multi
    def button_ok(self):
        self.ensure_one()
        res = []
        if self.date_end < self.date_start:
            raise UserError(u'开始日期不能大于结束日期！')

        buy_order_line = self.env['buy.order.line']
        for line in buy_order_line.search(self._get_domain(), order='goods_id'):
            is_buy = line.order_id.type == 'buy' and 1 or -1  # 是否购货订单
            # 以下分别为明细行上数量、采购额、未入库数量，退货时均取反
            qty = is_buy * line.quantity
            amount = is_buy * line.subtotal
            qty_not_in = is_buy * (line.quantity - line.quantity_in)
            # 创建跟踪表明细行（非小计行）
            track = self.env['buy.order.track'].create(
                self._prepare_track_line(line, qty, amount, qty_not_in))
            res.append(track.id)

        view = self.env.ref('buy.buy_order_track_tree')
        return {
            'name': u'采购订单跟踪表',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'res_model': 'buy.order.track',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
            'limit': 65535,
        }
