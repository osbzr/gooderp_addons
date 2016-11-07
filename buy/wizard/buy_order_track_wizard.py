# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class buy_order_track_wizard(models.TransientModel):
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
                             help=u'按指定供应商进行统计')
    goods_id = fields.Many2one('goods', u'商品',
                             help=u'按指定商品进行统计')
    order_id = fields.Many2one('buy.order', u'订单号',
                             help=u'按指定订单号进行统计')
    warehouse_dest_id = fields.Many2one('warehouse', u'仓库',
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
        if self.order_id:
            domain.append(('order_id.id', '=', self.order_id.id))
        if self.warehouse_dest_id:
            domain.append(('order_id.warehouse_dest_id', '=', self.warehouse_dest_id.id))
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
        }

    def _prepare_track_summary_line(self, qty, amount, qty_not_in):
        '''返回跟踪表小计行'''
        return {
            'goods_state': u'小计',
            'qty': qty,
            'amount': amount,
            'qty_not_in': qty_not_in,
        }

    @api.multi
    def button_ok(self):
        self.ensure_one()
        res = []
        if self.date_end < self.date_start:
            raise UserError(u'开始日期不能大于结束日期！')

        index = 0
        sum_qty = sum_amount = sum_not_in = 0   # 数量、金额、未入库数量合计
        total_qty = total_amount = total_not_in = 0  # 数量、金额、未入库数量小计
        line_ids = []
        buy_order_line = self.env['buy.order.line']
        for line in buy_order_line.search(self._get_domain(), order='goods_id'):
            line_ids.append(line)
            is_buy = line.order_id.type == 'buy' and 1 or -1 # 是否购货订单
            # 退货时数量、采购额、未入库数量均取反
            sum_qty += is_buy * line.quantity
            sum_amount += is_buy * line.subtotal
            sum_not_in += is_buy * (line.quantity - line.quantity_in)

        for line in buy_order_line.search(self._get_domain(), order='goods_id'):
            index += 1
            after_id = line_ids[index:] and line_ids[index]  # 下一个明细行
            if after_id:
                after = buy_order_line.search([('id', '=', after_id.id)])

            is_buy = line.order_id.type == 'buy' and 1 or -1 # 是否购货订单
            # 以下分别为明细行上数量、采购额、未入库数量，退货时均取反
            qty = is_buy * line.quantity
            amount = is_buy * line.subtotal
            qty_not_in = is_buy * (line.quantity - line.quantity_in)
            # 创建跟踪表明细行（非小计行）
            track = self.env['buy.order.track'].create(
                self._prepare_track_line(line, qty, amount, qty_not_in))
            res.append(track.id)

            if not after_id:  # 如果是最后一个明细行，则在最后增加一个小计行
                total_qty += qty
                total_not_in += qty_not_in
                total_amount += amount
                summary_last_track = self.env['buy.order.track'].create(
                    self._prepare_track_summary_line(total_qty, total_amount, total_not_in))
                res.append(summary_last_track.id)
                continue

            # 逐行累加数量、采购额和未入库数量
            total_qty += qty
            total_not_in += qty_not_in
            total_amount += amount
            if line.goods_id != after.goods_id:  # 如果下一个是不同商品，则增加一个小计行
                summary_track = self.env['buy.order.track'].create(
                    self._prepare_track_summary_line(total_qty, total_amount, total_not_in))
                res.append(summary_track.id)
                total_qty = total_amount = total_not_in = 0  # 计算不同的商品时先将初始值清零

        sum_track = self.env['buy.order.track'].create({
            'goods_state': u'合计',
            'qty': sum_qty,
            'amount': sum_amount,
            'qty_not_in': sum_not_in,
        })
        res.append(sum_track.id)
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
