# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class SellOrderTrackWizard(models.TransientModel):
    _name = 'sell.order.track.wizard'
    _description = u'销售订单跟踪表向导'

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
    partner_id = fields.Many2one('partner', u'客户',
                                 help=u'按指定客户进行统计')
    goods_id = fields.Many2one('goods', u'商品',
                               help=u'按指定商品进行统计')
    user_id = fields.Many2one('res.users', u'销售员',
                              help=u'按指定销售员进行统计')
    warehouse_id = fields.Many2one('warehouse', u'仓库',
                                   help=u'按指定仓库进行统计')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    def _get_domain(self):
        '''返回wizard界面上条件'''
        domain = [
            ('order_id.date', '>=', self.date_start),
            ('order_id.date', '<=', self.date_end),
            ('order_id.state', '!=', 'cancel')
        ]
        if self.goods_id:
            domain.append(('goods_id', '=', self.goods_id.id))
        if self.partner_id:
            domain.append(('order_id.partner_id', '=', self.partner_id.id))
        if self.user_id:
            domain.append(('order_id.user_id', '=', self.user_id.id))
        if self.warehouse_id:
            domain.append(('order_id.warehouse_id', '=', self.warehouse_id.id))
        return domain

    def _get_wh_out_date(self, line):
        '''对于一个 sell order line，返回一个出库日期'''
        wh_out_date = None
        wh_move_line = self.env['wh.move.line'].search([
            ('sell_line_id', '=', line.id),
            ('state', '=', 'done'),
        ])
        if len(wh_move_line) > 1:  # 如果是分批出库，则出库单明细行上的sell_line_id相同
            wh_out_date = wh_move_line[0].date
        else:
            wh_out_date = wh_move_line.date
        return wh_out_date

    def _prepare_track_line(self, line, qty, amount, qty_not_out):
        '''返回跟踪表明细行（非小计行）'''
        return {
            'goods_code': line.goods_id.code,
            'goods_id': line.goods_id.id,
            'attribute': line.attribute_id.name,
            'uom': line.uom_id.name,
            'date': line.order_id.date,
            'order_name': line.order_id.name,
            'user_id': line.order_id.user_id.id,
            'partner_id': line.order_id.partner_id.id,
            'warehouse_id': line.order_id.warehouse_id.id,
            'goods_state': line.order_id.goods_state,
            'qty': qty,
            'amount': amount,
            'qty_not_out': qty_not_out,
            'delivery_date': line.order_id.delivery_date,
            'wh_out_date': self._get_wh_out_date(line),  # 出库日期
            'note': line.note,
        }

    @api.multi
    def button_ok(self):
        self.ensure_one()
        res = []
        if self.date_end < self.date_start:
            raise UserError(u'开始日期不能大于结束日期！\n所选开始日期:%s 所选结束日期:%s' %
                            (self.date_start, self.date_end))

        sell_order_line = self.env['sell.order.line']
        for line in sell_order_line.search(self._get_domain(), order='goods_id'):
            is_sell = line.order_id.type == 'sell' and 1 or -1  # 是否销货订单
            # 以下分别为明细行上数量、销售额、未出库数量，退货时均取反
            qty = is_sell * line.quantity
            amount = is_sell * line.subtotal
            qty_not_out = is_sell * (line.quantity - line.quantity_out)

            # 创建跟踪表明细行（非小计行）
            track = self.env['sell.order.track'].create(
                self._prepare_track_line(line, qty, amount, qty_not_out))
            res.append(track.id)

        view = self.env.ref('sell.sell_order_track_tree')
        return {
            'name': u'销售订单跟踪表',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'res_model': 'sell.order.track',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
            'limit': 65535,
        }
