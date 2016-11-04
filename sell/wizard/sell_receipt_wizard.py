# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class sell_receipt_wizard(models.TransientModel):
    _name = 'sell.receipt.wizard'
    _description = u'销售收款一览表向导'

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
    c_category_id = fields.Many2one('core.category', u'客户类别',
                                    domain=[('type', '=', 'customer')],
                                    context={'type': 'customer'},
                                    help=u'按指定客户类别进行统计')
    partner_id = fields.Many2one('partner', u'客户',
                                 help=u'按指定客户进行统计')
    staff_id = fields.Many2one('staff', u'销售员',
                               help=u'按指定销售员进行统计')
    warehouse_id = fields.Many2one('warehouse', u'仓库',
                                   help=u'按指定仓库进行统计')

    def _get_domain(self):
        '''返回wizard界面上条件'''
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
        if self.warehouse_id:
            cond += ['|',('warehouse_id', '=', self.warehouse_id.id),
                     ('warehouse_dest_id', '=', self.warehouse_id.id)]
        return cond

    def _compute_receipt(self, delivery):
        '''计算该发货单的已收款'''
        receipt = 0
        for order in self.env['money.order'].search(
                    [('state', '=', 'done')], order='name'):
            for source in order.source_ids:
                if source.name.name == delivery.name:
                    receipt += source.this_reconcile
        return receipt

    def _prepare_sell_receipt(self, delivery):
        '''对于传入的发货单/退货单，为创建销售收款一览表准备数据'''
        self.ensure_one()
        factor = delivery.is_return and -1 or 1 # 如果是退货则金额均取反
        sell_amount = factor * (delivery.discount_amount + delivery.amount)
        discount_amount = factor * delivery.discount_amount
        amount = factor * delivery.amount
        partner_cost = factor * delivery.partner_cost
        order_type = not delivery.is_return and u'普通销售' or u'销售退回'
        warehouse = not delivery.is_return and delivery.warehouse_id or delivery.warehouse_dest_id
        # 计算该发货单的已收款
        receipt = self._compute_receipt(delivery)
        # 计算回款率
        receipt_rate = (amount + partner_cost) != 0 and (receipt / (amount + partner_cost)) * 100 or 0
        return {
            'c_category_id': delivery.partner_id.c_category_id.id,
            'partner_id': delivery.partner_id.id,
            'staff_id': delivery.staff_id.id,
            'type': order_type,
            'date': delivery.date,
            'order_name': delivery.name,
            'warehouse_id': warehouse.id,
            'sell_amount': sell_amount,
            'discount_amount': discount_amount,
            'amount': amount,
            'partner_cost': partner_cost,
            'receipt': receipt,
            'balance': amount + partner_cost - receipt,
            'receipt_rate': receipt_rate,
            'note': delivery.note,
        }

    @api.multi
    def button_ok(self):
        self.ensure_one()
        res = []
        if self.date_end < self.date_start:
            raise UserError(u'开始日期不能大于结束日期！')

        delivery_obj = self.env['sell.delivery']
        count = sum_receipt_rate = 0
        for delivery in delivery_obj.search(self._get_domain(), order='partner_id'):
            # 用查找到的发货单信息来创建一览表
            line = self.env['sell.receipt'].create(
                self._prepare_sell_receipt(delivery))
            res.append(line.id)
            count += 1
            sum_receipt_rate += line.receipt_rate

        # 创建一览表的合计行
        receipt_rate =  count != 0 and sum_receipt_rate / count or 0
        line_total = self.env['sell.receipt'].create({
            'order_name': u'平均回款率',
            'receipt_rate': receipt_rate,
        })
        res.append(line_total.id)
        return {
            'name': u'销售收款一览表',
            'view_mode': 'tree',
            'res_model': 'sell.receipt',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
            'limit': 65535,
        }
