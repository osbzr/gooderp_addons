# -*- coding: utf-8 -*-

from datetime import date
from openerp import models, fields, api
from openerp.exceptions import except_orm


class buy_order_track_wizard(models.TransientModel):
    _name = 'buy.order.track.wizard'
    _description = u'采购订单跟踪表向导'

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
    order_id = fields.Many2one('buy.order', u'订单号')

    @api.multi
    def button_ok(self):
        res = []
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

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

        index = 0
        sum_qty = sum_amount = sum_not_in = 0   # 数量、金额、未入库数量合计
        total_qty = total_amount = total_not_in = 0  # 数量、金额、未入库数量小计
        line_ids = []
        objOrderLine = self.env['buy.order.line']
        for line in objOrderLine.search(domain, order='goods_id'):
            line_ids.append(line)
            sum_qty += line.quantity
            sum_amount += line.subtotal
            sum_not_in += line.quantity - line.quantity_in

        for line in objOrderLine.search(domain, order='goods_id'):
            index += 1
            after_id = line_ids[index:] and line_ids[index:][0]  # 下一个明细行
            if after_id:
                after = objOrderLine.search([('id', '=', after_id.id)])

            wh_in_date = None
            objMoveLine = self.env['wh.move.line']
            wh_move_line = objMoveLine.search([
                ('buy_line_id', '=', line.id),
                ('state', '=', 'done')
            ])
            if len(wh_move_line) > 1:  # 如果是分批入库，则入库单明细行上的buy_line_id相同
                wh_in_date = wh_move_line[0].date
            else:
                wh_in_date = wh_move_line.date
            track = self.env['buy.order.track'].create({
                'goods_code': line.goods_id.code,
                'goods_id': line.goods_id.id,
                'attribute': line.attribute_id.name,
                'uom': line.uom_id.name,
                'date': line.order_id.date,
                'order_name': line.order_id.name,
                'partner_id': line.order_id.partner_id.id,
                'goods_state': line.order_id.goods_state,
                'qty': line.quantity,
                'amount': line.subtotal,
                'qty_not_in': line.quantity - line.quantity_in,
                'planned_date': line.order_id.planned_date,
                'wh_in_date': wh_in_date,  # 入库日期
                'note': line.note,
            })
            res.append(track.id)

            if not after_id:  # 如果是最后一个明细行，则在最后增加一个小计行
                total_qty += line.quantity
                total_not_in += line.quantity - line.quantity_in
                total_amount += line.subtotal
                summary_last_track = self.env['buy.order.track'].create({
                    'goods_state': u'小计',
                    'qty': total_qty,
                    'amount': total_amount,
                    'qty_not_in': total_not_in,
                })
                res.append(summary_last_track.id)
                continue

            if line.goods_id == after.goods_id:  # 如果下一个是相同商品，则累加数量、采购额和未入库数量
                total_qty += line.quantity
                total_not_in += line.quantity - line.quantity_in
                total_amount += line.subtotal
            elif line.goods_id != after.goods_id:  # 如果下一个是不同商品，则增加一个小计行
                total_qty += line.quantity
                total_not_in += line.quantity - line.quantity_in
                total_amount += line.subtotal
                summary_track = self.env['buy.order.track'].create({
                    'goods_state': u'小计',
                    'qty': total_qty,
                    'amount': total_amount,
                    'qty_not_in': total_not_in,
                })
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
            'limit': 300,
        }
