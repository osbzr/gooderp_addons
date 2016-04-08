# -*- coding: utf-8 -*-

from datetime import date
from openerp import models, fields, api
from openerp.exceptions import except_orm


class buy_summary_goods_wizard(models.TransientModel):
    _name = 'buy.summary.goods.wizard'
    _description = u'采购汇总表（按商品）向导'

    @api.model
    def _default_date_start(self):
        return self.env.user.company_id.start_date

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(u'开始日期', default=_default_date_start)
    date_end = fields.Date(u'结束日期', default=_default_date_end)
    partner_id = fields.Many2one('partner', u'供应商')
    goods_id = fields.Many2one('goods', u'产品')

    @api.multi
    def button_ok(self):
        res = []
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        domain = [('move_id.date', '>=', self.date_start),
                  ('move_id.date', '<=', self.date_end),
                  ('move_id.origin', 'like', 'buy'),
                  ('state', '=', 'done'),
                  ]

        if self.goods_id:
            domain.append(('goods_id', '=', self.goods_id.id))
        if self.partner_id:
            domain.append(('move_id.partner_id', '=', self.partner_id.id))

        i = 0
        line_ids = []
        total_qty = total_qty_uos = total_price = total_amount = total_tax_amount = total_subtotal = 0
        qty = qty_uos = amount = price = tax_amount = subtotal = 0
        for line in self.env['wh.move.line'].search(domain, order='move_id'):
            line_ids.append(line)
        for line_id in line_ids:    # 外循环，line_ids是动态变化的
            line = self.env['wh.move.line'].search([('id', '=', line_id.id)])
            # 先将当前行的数量、金额等累加
            qty = line.goods_qty
            qty_uos = line.goods_uos_qty
            amount = line.amount
            price = line.price
            tax_amount = line.tax_amount
            subtotal = line.subtotal
            if line.move_id.origin and 'return' in line.move_id.origin:
                # 如果wh.move.line是采购退货，则将数量和金额取反
                qty = - line.goods_qty
                qty_uos = - line.goods_uos_qty
                amount = - line.amount
                price = amount / qty
                tax_amount = - line.tax_amount
                subtotal = - line.subtotal
            i += 1  # 当前是第 i 次外循环
            length = len(line_ids)  # 当前的line是动态变化的，统计一个line后将其移除
            index = 0   # 记录当前line是所有line中第几条数据
            last_index = 0  # 记录上一次数据的index
            deleted = False # 标记某行是否删除
            for index in range(length - i + 1): # 内循环
                length = len(line_ids)
                if index == 0:
                    index = i
                else:
                    index = last_index + 1

                if not deleted:
                    last_index = index
                else:
                    index = last_index
                    deleted = False

                after_id = line_ids[index:] and line_ids[index:][0]
                if not after_id:    # 如果是最后一条数据，则不去查找下一条
                    break
                after = self.env['wh.move.line'].search([('id', '=', after_id.id)])
                if line.move_id.origin and 'return' in line.move_id.origin:
                    # 如果是退货
                    if (line.goods_id.id == after.goods_id.id
                        and line.attribute_id.id == after.attribute_id.id
                        and  line.warehouse_dest_id.id == after.warehouse_dest_id.id):
                        qty += (-1) * after.goods_qty
                        qty_uos += (-1) * after.goods_uos_qty
                        amount += (-1) * after.amount
                        price = amount / qty
                        tax_amount += (-1) * after.tax_amount
                        subtotal += (-1) * after.subtotal
                        if index == length:
                            del line_ids[index-1]
                        else:
                            del line_ids[index]
                            deleted = True
                            last_index = index
                else:
                    # 如果是购货
                    if (line.goods_id.id == after.goods_id.id
                        and line.attribute_id.id == after.attribute_id.id
                        and  line.warehouse_dest_id.id == after.warehouse_dest_id.id):
                        qty += after.goods_qty
                        qty_uos += after.goods_uos_qty
                        amount += after.amount
                        price = amount / qty
                        tax_amount += after.tax_amount
                        subtotal += after.subtotal
                        if index == length:
                            del line_ids[index-1]
                        else:
                            del line_ids[index]
                            deleted = True
                            last_index = index
            summary = self.env['buy.summary.goods'].create({
                    'order_name': line.move_id.name,
                    'goods_categ_id': line.goods_id.category_id.id,
                    'goods_code': line.goods_id.code,
                    'goods_id': line.goods_id.id,
                    'attribute': line.attribute_id.name,
                    'warehouse_dest': line.warehouse_dest_id.name,
                    'uos': line.uos_id and line.uos_id.name or '',
                    'qty_uos': qty_uos,
                    'uom': line.uom_id.name,
                    'qty': qty,
                    'price': price,
                    'amount': amount,
                    'tax_amount': tax_amount,
                    'subtotal': subtotal,
                })
            res.append(summary.id)

            total_qty += summary.qty
            total_qty_uos += summary.qty_uos
            total_amount += summary.amount
            total_price = total_amount / total_qty
            total_tax_amount += summary.tax_amount
            total_subtotal += summary.subtotal
        sum_summary = self.env['buy.summary.goods'].create({
            'warehouse_dest': u'合计',
            'qty_uos': total_qty_uos,
            'qty': total_qty,
            'price': total_price,
            'amount': total_amount,
            'tax_amount': total_tax_amount,
            'subtotal': total_subtotal,
        })
        res.append(sum_summary.id)

        view = self.env.ref('buy.buy_summary_goods_tree')
        return {
            'name': u'采购汇总表（按商品）',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'res_model': 'buy.summary.goods',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
            'limit': 300,
        }
