# -*- coding: utf-8 -*-

from datetime import date
from openerp import models, fields, api
from openerp.exceptions import except_orm


class sell_receipt_wizard(models.TransientModel):
    _name = 'sell.receipt.wizard'
    _description = u'销售收款一览表向导'

    @api.model
    def _default_date_start(self):
        return self.env.user.company_id.start_date

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(u'开始日期', default=_default_date_start)
    date_end = fields.Date(u'结束日期', default=_default_date_end)
    c_category_id = fields.Many2one('core.category', u'客户类别',
                                    domain=[('type', '=', 'customer')],
                                    context={'type': 'customer'})
    partner_id = fields.Many2one('partner', u'客户')
    staff_id = fields.Many2one('staff', u'销售员')

    @api.multi
    def button_ok(self):
        res = []
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        cond = [('date', '>=', self.date_start),
                ('date', '<=', self.date_end),
                ('state', '=', 'done')]
        if self.c_category_id:
            cond.append(
                ('partner_id.c_category_id', '=', self.c_category_id.id)
            )
        if self.partner_id:
            cond.append(('partner_id', '=', self.partner_id.id))
        if self.staff_id:
            cond.append(('staff_id', '=', self.staff_id.id))
        delivery_obj = self.env['sell.delivery']
        for delivery in delivery_obj.search(cond, order='partner_id'):
            sell_amount = delivery.discount_amount + delivery.amount
            discount_amount = delivery.discount_amount
            amount = delivery.amount
            receipt = delivery.receipt
            balance = delivery.debt
            if not delivery.is_return:
                order_type = u'普通销售'
            elif delivery.is_return:
                order_type = u'销售退回'
                sell_amount = - sell_amount
                discount_amount = - discount_amount
                amount = - amount
                receipt = - receipt
                balance = - balance
            # 用查找到的发货单信息来创建一览表
            line = self.env['sell.receipt'].create({
                'c_category_id': delivery.partner_id.c_category_id.id,
                'partner_id': delivery.partner_id.id,
                'staff_id': delivery.staff_id.id,
                'type': order_type,
                'date': delivery.date,
                'order_name': delivery.name,
                'sell_amount': sell_amount,
                'discount_amount': discount_amount,
                'amount': amount,
                'receipt': receipt,
                'balance': balance,
                'note': delivery.note,
            })
            res.append(line.id)

            # 用查找到的发货单产生的收款单信息来创建一览表
            receipt = 0
            for order in self.env['money.order'].search([]):
                for source in order.source_ids:
                    if source.name.name == delivery.name:
                        # 创建收款单行line2
                        line2 = self.env['sell.receipt'].create({
                            'type': u'收款',
                            'date': source.date,
                            'order_name': source.money_id.name,
                            'receipt': source.this_reconcile,
                            'balance': source.to_reconcile,
                        })
                        receipt += source.this_reconcile
                        res.append(line2.id)

            # 创建一览表的小计行
            if amount == 0 and receipt == 0:
                receipt_rate = 100
            else:
                receipt_rate = (receipt / amount) * 100
            line_subtotal = self.env['sell.receipt'].create({
                'order_name': u'小计',
                'sell_amount': sell_amount,
                'discount_amount': discount_amount,
                'amount': amount,
                'receipt': receipt,
                'balance': amount - receipt,
                'receipt_rate': receipt_rate,
            })
            res.append(line_subtotal.id)
        return {
            'name': u'销售收款一览表',
            'view_mode': 'tree',
            'res_model': 'sell.receipt',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
            'limit': 300,
        }
