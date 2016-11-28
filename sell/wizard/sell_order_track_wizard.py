# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class sell_order_track_wizard(models.TransientModel):
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
    staff_id = fields.Many2one('staff', u'销售员',
                               help=u'按指定销售员进行统计')
    warehouse_id = fields.Many2one('warehouse', u'仓库',
                                   help=u'按指定仓库进行统计')

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
        if self.staff_id:
            domain.append(('order_id.staff_id', '=', self.staff_id.id))
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
            'staff_id': line.order_id.staff_id.id,
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

    def _prepare_track_summary_line(self, total_qty, total_amount, total_not_out):
        '''返回跟踪表小计行'''
        return {
            'goods_state': u'小计',
            'qty': total_qty,
            'amount': total_amount,
            'qty_not_out': total_not_out,
        }

    @api.multi
    def button_ok(self):
        self.ensure_one()
        res = []
        if self.date_end < self.date_start:
            raise UserError(u'开始日期不能大于结束日期！\n所选开始日期:%s 所选结束日期:%s'%(self.date_start, self.date_end))

        index = 0
        sum_qty = sum_amount = sum_not_out = 0  # 数量、金额、未出库数量合计
        total_qty = total_amount = total_not_out = 0    # 数量、金额、未出库数量小计
        line_ids = []
        sell_order_line = self.env['sell.order.line']
        for line in sell_order_line.search(self._get_domain(), order='goods_id'):
            line_ids.append(line)
            is_sell = line.order_id.type == 'sell' and 1 or -1 # 是否销货订单
            # 退货时数量、销售额、未出库数量均取反
            sum_qty += is_sell * line.quantity
            sum_amount += is_sell * line.subtotal
            sum_not_out += is_sell * (line.quantity - line.quantity_out)

        for line in sell_order_line.search(self._get_domain(), order='goods_id'):
            index += 1
            after_id = line_ids[index:] and line_ids[index]  # 下一个明细行
            if after_id:
                after = sell_order_line.search([('id', '=', after_id.id)])

            is_sell = line.order_id.type == 'sell' and 1 or -1 # 是否销货订单
            # 以下分别为明细行上数量、销售额、未出库数量，退货时均取反
            qty = is_sell * line.quantity
            amount = is_sell * line.subtotal
            qty_not_out = is_sell * (line.quantity - line.quantity_out)

            # 创建跟踪表明细行（非小计行）
            track = self.env['sell.order.track'].create(
                self._prepare_track_line(line, qty, amount, qty_not_out))
            res.append(track.id)

            if not after_id:  # 如果是最后一个明细行，则在最后增加一个小计行
                total_qty += qty
                total_not_out += qty_not_out
                total_amount += amount
                summary_last_track = self.env['sell.order.track'].create(
                    self._prepare_track_summary_line(total_qty, total_amount, total_not_out))
                res.append(summary_last_track.id)
                continue

            # 如果下一个是相同商品，则累加数量、销售额和未出库数量
            total_qty += qty
            total_not_out += qty_not_out
            total_amount += amount
            if line.goods_id != after.goods_id:  # 如果下一个是不同商品，则增加一个小计行
                summary_track = self.env['sell.order.track'].create(
                    self._prepare_track_summary_line(total_qty, total_amount, total_not_out))
                res.append(summary_track.id)
                total_qty = total_amount = total_not_out = 0  # 计算不同的商品时先将初始值清零

        sum_track = self.env['sell.order.track'].create({
                    'goods_state': u'合计',
                    'qty': sum_qty,
                    'amount': sum_amount,
                    'qty_not_out': sum_not_out,
                })
        res.append(sum_track.id)
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
