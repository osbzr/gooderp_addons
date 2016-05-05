# -*- coding: utf-8 -*-

from datetime import date
from openerp import models, fields, api
from openerp.exceptions import except_orm


class buy_payment_wizard(models.TransientModel):
    _name = 'buy.payment.wizard'
    _description = u'采购付款一览表向导'

    @api.model
    def _default_date_start(self):
        return self.env.user.company_id.start_date

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(u'开始日期', default=_default_date_start)
    date_end = fields.Date(u'结束日期', default=_default_date_end)
    s_category_id = fields.Many2one('core.category', u'供应商类别')
    partner_id = fields.Many2one('partner', u'供应商')
    order_id = fields.Many2one('buy.receipt', u'采购单号')

    @api.multi
    def button_ok(self):
        res = []
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        cond = [('date', '>=', self.date_start),
                ('date', '<=', self.date_end),
                ('state', '=', 'done')]
        if self.s_category_id:
            cond.append(
                ('partner_id.s_category_id', '=', self.s_category_id.id)
            )
        if self.partner_id:
            cond.append(('partner_id', '=', self.partner_id.id))
        if self.order_id:
            cond.append(('name', '=', self.order_id.id))
        receipt_obj = self.env['buy.receipt']
        count = sum_payment_rate = 0    # 行数及所有行的付款率之和
        for receipt in receipt_obj.search(cond, order='partner_id,date'):
            purchase_amount = receipt.discount_amount + receipt.amount
            discount_amount = receipt.discount_amount
            amount = receipt.amount
            # 计算该入库单的已付款和应付款余额
            payment = balance = 0
            for order in self.env['money.order'].search(
                        [('state', '=', 'done')], order='name'):
                for source in order.source_ids:
                    if source.name.name == receipt.name:
                        payment += source.this_reconcile
            # 如果是退货则金额均取反
            if not receipt.is_return:
                order_type = u'普通采购'
            elif receipt.is_return:
                order_type = u'采购退回'
                purchase_amount = - purchase_amount
                discount_amount = - discount_amount
                amount = - amount
            # 计算付款率
            if amount == 0 and payment == 0:
                payment_rate = 100
            else:
                payment_rate = (payment / amount) * 100
            # 用查找到的入库单信息来创建一览表
            line = self.env['buy.payment'].create({
                'partner_id': receipt.partner_id.id,
                'type': order_type,
                'date': receipt.date,
                'order_name': receipt.name,
                'purchase_amount': purchase_amount,
                'discount_amount': discount_amount,
                'amount': amount,
                'payment': payment,
                'balance': amount - payment,
                'payment_rate': payment_rate,
                'note': receipt.note,
            })
            res.append(line.id)
            count += 1
            sum_payment_rate += line.payment_rate

        # 创建一览表的平均付款率行
        if sum_payment_rate == 0 and count == 0:
            payment_rate = 100
        else:
            payment_rate = sum_payment_rate / count
        line_total = self.env['buy.payment'].create({
            'order_name': u'平均付款率',
            'payment_rate': payment_rate,
        })
        res.append(line_total.id)
        return {
            'name': u'采购付款一览表',
            'view_mode': 'tree',
            'res_model': 'buy.payment',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
            'limit': 300,
        }
