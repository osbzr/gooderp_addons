# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class SellReceiptWizard(models.TransientModel):
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
                                    help=u'只统计选定的客户类别')
    partner_id = fields.Many2one('partner', u'客户',
                                 help=u'只统计选定的客户')
    user_id = fields.Many2one('res.users', u'销售员',
                              help=u'只统计选定的销售员')
    warehouse_id = fields.Many2one('warehouse', u'仓库',
                                   help=u'只统计选定的仓库')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

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
        if self.user_id:
            cond.append(('user_id', '=', self.user_id.id))
        if self.warehouse_id:
            cond += ['|', ('warehouse_id', '=', self.warehouse_id.id),
                     ('warehouse_dest_id', '=', self.warehouse_id.id)]
        return cond

    def _compute_receipt(self, delivery):
        '''计算该发货单的已收款'''
        invoices = self.env['money.invoice'].search([
            ('name', '=', delivery.name),
            ('state', '=', 'done')])
        receipt = sum([invoice.reconciled for invoice in invoices])
        return receipt

    def _prepare_sell_receipt(self, delivery):
        '''对于传入的发货单/退货单，为创建销售收款一览表准备数据'''
        self.ensure_one()
        factor = delivery.is_return and -1 or 1  # 如果是退货则金额均取反
        sell_amount = factor * (delivery.discount_amount + delivery.amount)
        discount_amount = factor * delivery.discount_amount
        amount = factor * delivery.amount
        partner_cost = factor * delivery.partner_cost
        order_type = not delivery.is_return and u'普通销售' or u'销售退回'
        warehouse = not delivery.is_return and delivery.warehouse_id or delivery.warehouse_dest_id
        # 计算该发货单的已收款
        receipt = self._compute_receipt(delivery)
        # 计算回款率
        receipt_rate = (amount + partner_cost) != 0 and (receipt /
                                                         (amount + partner_cost)) * 100 or 0
        return {
            'c_category_id': delivery.partner_id.c_category_id.id,
            'partner_id': delivery.partner_id.id,
            'user_id': delivery.user_id.id,
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

    def compute_partner_receipt(self, partner):
        """该客户所有收款单未核销金额合计数"""
        orders = self.env['money.order'].search([
            ('state', '=', 'done'),
            ('partner_id', '=', partner.id)])
        sum_amount = sum(order.to_reconcile for order in orders)
        return sum_amount

    @api.multi
    def button_ok(self):
        self.ensure_one()
        res = []
        dict_part = {}
        if self.date_end < self.date_start:
            raise UserError(u'开始日期不能大于结束日期！\n 所选的开始日期:%s 结束日期:%s' %
                            (self.date_start, self.date_end))

        delivery_obj = self.env['sell.delivery']
        for delivery in delivery_obj.search(self._get_domain(), order='partner_id'):
            if not dict_part.has_key(delivery.partner_id):
                dict_part[delivery.partner_id] = delivery
            else:
                dict_part[delivery.partner_id] += delivery
        for partner, deliverys in dict_part.iteritems():
            for delivery in deliverys:
                # 用查找到的发货单信息来创建一览表
                line = self.env['sell.receipt'].create(
                    self._prepare_sell_receipt(delivery))
                res.append(line.id)
            # 增加一行，编号是未核销预收款，已收款是该客户所有收款单未核销金额合计数，应收款余额为负的预收款
            summary_line = self.env['sell.receipt'].create({
                'partner_id': partner.id,
                'order_name': u'未核销预收款',
                'receipt': self.compute_partner_receipt(partner),
                'balance': -self.compute_partner_receipt(partner),
            })
            res.append(summary_line.id)

        return {
            'name': u'销售收款一览表',
            'view_mode': 'tree',
            'res_model': 'sell.receipt',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
            'limit': 65535,
        }
