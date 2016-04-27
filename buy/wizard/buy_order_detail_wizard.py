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

    @api.multi
    def button_ok(self):
        res = []
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        # 先查找采购明细表，若有数据则清空
        for detail in self.env['buy.order.detail'].search([]):
            detail.unlink()

        domain = [('move_id.date', '>=', self.date_start),
                  ('move_id.date', '<=', self.date_end),
                  ('move_id.origin', 'like', 'buy'),
                  ('state', '=', 'done'),
                  ]

        if self.goods_id:
            domain.append(('goods_id', '=', self.goods_id.id))
        if self.partner_id:
            domain.append(('move_id.partner_id', '=', self.partner_id.id))
        if self.order_id:
            buy_receipt = self.env['buy.receipt'].search(
                                [('id', '=', self.order_id.id)])
            domain.append(('move_id.id', '=', buy_receipt.buy_move_id.id))

        order_type = ''
        for line in self.env['wh.move.line'].search(domain, order='move_id'):
            if line.move_id.origin and 'return' in line.move_id.origin:
                order_type = '退货'
            else:
                order_type = '购货'
            detail = self.env['buy.order.detail'].create({
                'date': line.move_id.date,
                'order_name': line.move_id.name,
                'type': order_type,
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

        view = self.env.ref('buy.buy_order_detail_tree')
        return {
            'name': u'采购明细表',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'res_model': 'buy.order.detail',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
            'limit': 300,
        }
