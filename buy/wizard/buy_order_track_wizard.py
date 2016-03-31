# -*- coding: utf-8 -*-

from datetime import date, timedelta
from openerp import models, fields, api
from openerp.exceptions import except_orm


class buy_order_track_wizard(models.TransientModel):
    _name = 'buy.order.track.wizard'
    _description = u'采购订单跟踪表向导'

    @api.model
    def _default_date_start(self):
        return date.today().replace(day=1).strftime('%Y-%m-%d')

    @api.model
    def _default_date_end(self):
        now = date.today()
        next_month = now.month == 12 and now.replace(year=now.year + 1,
            month=1, day=1) or now.replace(month=now.month + 1, day=1)

        return (next_month - timedelta(days=1)).strftime('%Y-%m-%d')

    date_start = fields.Date(u'开始日期', default=_default_date_start)
    date_end = fields.Date(u'结束日期', default=_default_date_end)
    partner_id = fields.Many2one('partner', u'供应商')
    goods_id = fields.Many2one('goods', u'产品')

    @api.multi
    def button_ok(self):
        date_start = self.date_start
        date_end = self.date_end
        if date_start and date_end and date_end < date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        partner_id = self.partner_id
        goods_id = self.goods_id
        domain = [('order_id.date', '>=', date_start), ('order_id.date', '<=', date_end)]
        res = []
        goods_ids = None
        if goods_id:
            goods_ids = goods_id
            domain.append(('goods_id', '=', goods_id.id))
        else:
            goods_ids = self.env['goods'].search([])
        if partner_id:
            domain.append(('partner_id', '=', partner_id.id))

        for line in self.env['buy.order.line'].search(domain):
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
                    'wh_in_date': line.order_id.date,   # FIXME: 找出入库日期
                    'note': line.note,
                })
            res.append(track.id)

        index = 0
        total_qty = total_amount = total_not_in =0
        track_ids = []
        for track in self.env['buy.order.track'].search([('id', 'in', res)], order='goods_code,date'):
            track_ids.append(track)
        for track in self.env['buy.order.track'].search([('id', 'in', res)], order='goods_code,date'):
            index += 1
            after_id = track_ids[index:] and track_ids[index:][0] # 下一个明细行
            if after_id:
                after = self.env['buy.order.track'].search([('id', '=', after_id.id)])
            else:
                total_qty = track.qty
                total_not_in = track.qty_not_in
                total_amount = track.amount
            if track.goods_id == after.goods_id:
                total_qty += track.qty
                total_not_in += track.qty_not_in
                total_amount += track.amount
                print index,track.order_name
            elif track.goods_id != after.goods_id:
                total_qty += track.qty
                total_not_in += track.qty_not_in
                total_amount += track.amount
                summary_track = self.env['buy.order.track'].create({
                    'goods_state': u'小计',
                    'qty': total_qty,
                    'amount': total_amount,
                    'qty_not_in': total_not_in,
                })
                res.append(summary_track.id)
            if not after_id:
                summary_last_track = self.env['buy.order.track'].create({
                    'goods_state': u'小计',
                    'qty': track.qty,
                    'amount': track.amount,
                    'qty_not_in': track.qty_not_in,
                })
                res.append(summary_last_track.id)
        view = self.env.ref('buy.buy_order_track_tree')
        return {
            'name': u'采购订单跟踪表:',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'res_model': 'buy.order.track',
            'type': 'ir.actions.act_window',
            'domain':[('id','in',res)],
            'limit': 300,
        }
