# -*- coding: utf-8 -*-

from datetime import date
from openerp import models, fields, api
from openerp.exceptions import except_orm


class sell_order_detail_wizard(models.TransientModel):
    _name = 'sell.order.detail.wizard'
    _description = u'销售明细表向导'

    @api.model
    def _default_date_start(self):
        return self.env.user.company_id.start_date

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(u'开始日期', default=_default_date_start)
    date_end = fields.Date(u'结束日期', default=_default_date_end)
    partner_id = fields.Many2one('partner', u'客户')
    goods_id = fields.Many2one('goods', u'产品')
    staff_id = fields.Many2one('staff', u'销售员')

    @api.multi
    def button_ok(self):
        res = []
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        domain = [('move_id.date', '>=', self.date_start),
                  ('move_id.date', '<=', self.date_end),
                  ('move_id.origin', 'like', 'sell.delivery'),
                  ('state', '=', 'done'),
                  ]

        if self.goods_id:
            domain.append(('goods_id', '=', self.goods_id.id))
        if self.partner_id:
            domain.append(('move_id.partner_id', '=', self.partner_id.id))

        order_type = ''
        total_qty = total_price = total_amount = total_tax_amount = total_subtotal = 0
        for line in self.env['wh.move.line'].search(domain, order='move_id'):
            if line.move_id.origin and 'return' in line.move_id.origin:
                order_type = u'退货'
            else:
                order_type = u'销货'
            sell_delivery = self.env['sell.delivery'].search(
                                [('sell_move_id', '=', line.move_id.id)])
            if sell_delivery:
                staff_id = sell_delivery.staff_id and sell_delivery.staff_id.id or ''
            detail = self.env['sell.order.detail'].create({
                    'date': line.move_id.date,
                    'order_name': line.move_id.name,
                    'type': order_type,
                    'staff_id': staff_id,
                    'partner_id': line.move_id.partner_id.id,
                    'goods_code': line.goods_id.code,
                    'goods_id': line.goods_id.id,
                    'attribute': line.attribute_id.name,
                    'uom': line.uom_id.name,
                    'warehouse_dest': line.warehouse_dest_id.name,
                    'qty': line.goods_qty,
                    'price': line.price,
                    'amount': line.amount,
                    'tax_amount': line.tax_amount,
                    'subtotal': line.subtotal,
                    'note': line.note,
                })
            res.append(detail.id)

            total_qty += line.goods_qty
            total_price += line.price
            total_amount += line.amount
            total_tax_amount += line.tax_amount
            total_subtotal += line.subtotal
        sum_detail = self.env['sell.order.detail'].create({
            'warehouse_dest': u'合计',
            'qty': total_qty,
            'price': total_price,
            'amount': total_amount,
            'tax_amount': total_tax_amount,
            'subtotal': total_subtotal,
        })
        res.append(sum_detail.id)

        view = self.env.ref('sell.sell_order_detail_tree')
        cond = [('id', 'in', res)]
        if self.staff_id:
            cond.append(('staff_id', '=', self.staff_id.id))
        return {
            'name': u'销售明细表',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'res_model': 'sell.order.detail',
            'type': 'ir.actions.act_window',
            'domain': cond,
            'limit': 300,
        }
