# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016  开阖软件(<http://www.osbzr.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tools import float_compare, float_is_zero

# 购货订单审核状态可选值
COST_ORDER_STATES = [
    ('draft', u'未审核'),
    ('done', u'已审核'),
    ('cancel', u'已中止'),
    ('cancel', u'已作废')]

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
}


class CostOrder(models.Model):
    _name = "cost.order"
    _inherit = ['mail.thread']
    _description = u"费用/服务采购单"
    _order = 'date desc, id desc'

    @api.one
    @api.depends('line_ids.amount', 'line_ids.tax_amount')
    def _compute_amount(self):
        '''当订单行和优惠金额改变时，改变成交金额'''
        self.amount = sum(line.amount for line in self.line_ids)
        self.tax_amount = sum(line.tax_amount for line in self.line_ids)

    partner_id = fields.Many2one('partner', u'供应商', states=READONLY_STATES,
                                 ondelete='restrict',
                                 help=u'供应商')
    date = fields.Date(u'单据日期', states=READONLY_STATES,
                       default=lambda self: fields.Date.context_today(self),
                       index=True, copy=False, help=u"默认是订单创建日期")
    name = fields.Char(u'单据编号', index=True, copy=False,
                       help=u"服务订单的唯一编号，当创建时它会自动生成下一个编号。")
    line_ids = fields.One2many('cost.order.line', 'order_id', u'服务明细行',
                               states=READONLY_STATES, copy=True,
                               help=u'采购服务的明细行，不能为空')
    note = fields.Text(u'备注', help=u'单据备注')
    prepayment = fields.Float(u'预付款', states=READONLY_STATES,
                              digits=dp.get_precision('Amount'),
                              help=u'输入预付款审核购货订单，会产生一张付款单')
    bank_account_id = fields.Many2one('bank.account', u'结算账户',
                                      ondelete='restrict',
                                      help=u'用来核算和监督企业与其他单位或个人之间的债权债务的结算情况')
    invoice_ids = fields.Many2many('money.invoice',
                                   'cost_invoice',
                                   'cost_ids',
                                   'invoice_ids',
                                   u'费用凭证', copy=False)
    wm_ids = fields.Many2many('cost.line',
                              'wearhouse_move_cost',
                              'cost_order',
                              'move_cost_line',
                              u'服务费用与仓库', copy=False)
    wh_move_ids = fields.Many2many('wh.move',
                                   'cost_move',
                                   'cost_ids',
                                   'move_ids',
                                   u'费用分摊出入库明细', copy=False)
    approve_uid = fields.Many2one('res.users', u'审核人',
                                  copy=False, ondelete='restrict',
                                  help=u'审核单据的人')
    state = fields.Selection(COST_ORDER_STATES, u'审核状态', readonly=True,
                             help=u"购货订单的审核状态", index=True, copy=False,
                             default='draft')
    amount = fields.Float(u'合计金额', store=True, readonly=True,
                          compute='_compute_amount', track_visibility='always',
                          digits=dp.get_precision('Amount'),
                          help=u'总金额减去优惠金额')
    tax_amount = fields.Float(u'合计税额', store=True, readonly=True,
                              compute='_compute_amount', track_visibility='always',
                              digits=dp.get_precision('Amount'))
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    #pay_ids=fields.One2many("payment.plan","cost_id",string=u"付款计划", help=u'分批付款时使用付款计划')

    def _get_vals(self):
        '''返回创建 money_order 时所需数据'''
        money_lines = [{
            'bank_id': self.bank_account_id.id,
            'amount': self.prepayment,
        }]
        return {
            'partner_id': self.partner_id.id,
            'date': fields.Date.context_today(self),
            'line_ids':
            [(0, 0, line) for line in money_lines],
            'amount': self.amount,
            'reconciled': self.prepayment,
            'to_reconcile': self.amount,
            'state': 'draft',
            'origin_name': self.name,
        }

    @api.one
    def generate_payment_order(self):
        '''由购货订单生成付款单'''
        # 入库单/退货单
        if self.prepayment:
            money_order = self.with_context(type='pay').env['money.order'].create(
                self._get_vals()
            )
            return money_order

    @api.one
    def _amount_to_invoice(self):
        '''服务费用产生结算单'''
        invoice_id = False
        if not float_is_zero(self.amount, 2):
            for line in self.line_ids:
                invoice_id = self.env['money.invoice'].create({
                    'name': self.name,
                    'partner_id': self.partner_id.id,
                    'category_id': line.category_id.id,
                    'date': self.date,
                    'amount': line.subtotal,
                    'reconciled': 0,
                    'to_reconcile': line.subtotal,
                    'tax_amount': line.tax_amount,
                    'date_due': self.date,
                    'note': line.note,
                    'state': 'draft',
                })
                self.invoice_ids = [(4, invoice_id.id)]
        return self.invoice_ids

    @api.one
    def _create_mv_cost(self):
        """
        在所关联的入库单/发货单上创建费用行
        :return:
        """
        all_amount = sum(wh_move_line.amount for wh_move_line in self.env['wh.move.line'].search(
            [('move_id', 'in', self.wh_move_ids.ids)]))
        for mv in self.wh_move_ids:

            if mv.origin == 'buy.receipt.buy':
                buy_id = self.env['buy.receipt'].search(
                    [('buy_move_id', '=', mv.id)])
                mv_amount = sum(mv_line.amount for mv_line in mv.line_in_ids)
                for cost_line in self.line_ids:
                    cost_mv_in_id = self.env['cost.line'].create({
                        'partner_id': self.partner_id.id,
                        'category_id': cost_line.category_id.id,
                        'amount': cost_line.amount * (mv_amount / all_amount),
                        'tax': cost_line.tax_amount * (mv_amount / all_amount),
                        'buy_id': buy_id.id
                    })
                    self.wm_ids = [(4, cost_mv_in_id.id)]

            if mv.origin == 'sell.delivery.sell':
                sell_id = self.env['sell.delivery'].search(
                    [('sell_move_id', '=', mv.id)])
                mv_amount = sum(mv_line.amount for mv_line in mv.line_out_ids)
                for cost_line in self.line_ids:
                    cost_mv_out_id = self.env['cost.line'].create({
                        'partner_id': self.partner_id.id,
                        'category_id': cost_line.category_id.id,
                        'amount': cost_line.amount * (mv_amount / all_amount),
                        'tax': cost_line.tax_amount * (mv_amount / all_amount),
                        'sell_id': sell_id.id
                    })
                    self.wm_ids = [(4, cost_mv_out_id.id)]

    @api.one
    def cost_order_confim(self):
        '''审核服务订单'''
        if not self.name:
            self.update(
                {'name': self.env['ir.sequence'].next_by_code('cost.order') or '/'})
        if self.state == 'done':
            raise UserError(u'请不要重复审核！')
        if self.state == 'cancel':
            raise UserError(u'请不要审核已中止的订单！')
        if not self.line_ids:
            raise UserError(u'请输入服务明细行！')
        if not self.bank_account_id and self.prepayment:
            raise UserError(u'预付款不为空时，请选择结算账户！')
        # 采购预付款生成付款单
        self.generate_payment_order()
        self._create_mv_cost()
        self._amount_to_invoice()
        self.state = 'done'
        self.approve_uid = self._uid

    @api.one
    def cost_order_draft(self):
        '''反审核服务订单'''
        if self.state == 'draft':
            raise UserError(u'请不要重复反审核！')

        for mv_id in self.wm_ids:
            cost_line_id = mv_id
            self.wm_ids = [(3, mv_id.id)]
            cost_line_id.unlink()

        for invoice in self.invoice_ids:
            invoice_id = invoice
            self.invoice_ids = [(3, invoice.id)]
            invoice_id.money_invoice_draft()
            invoice_id.unlink()

        # 查找产生的付款单并反审核，删除
        money_order = self.env['money.order'].search(
            [('origin_name', '=', self.name)])
        if money_order:
            money_order.money_order_draft()
            money_order.unlink()

        self.state = 'draft'
        self.approve_uid = ''


class CostOrderLine(models.Model):
    _name = 'cost.order.line'
    _description = u'费用单明细'

    @api.one
    @api.depends('amount', 'tax_amount')
    def _compute_all_amount(self):
        self.subtotal = self.amount + self.tax_amount  # 价税合计

    order_id = fields.Many2one('cost.order', u'订单编号', index=True,
                               required=True, ondelete='cascade',
                               help=u'关联订单的编号')
    category_id = fields.Many2one('core.category', u'类别',
                                  required=True,
                                  ondelete='restrict',
                                  help=u'分类：采购')
    amount = fields.Float(u'金额',
                          digits=dp.get_precision('Amount'),
                          help=u'金额  = 价税合计  - 税额')
    tax_amount = fields.Float(u'税额',
                              help=u'增值税专用发票中的税额')
    subtotal = fields.Float(u'价税合计', compute=_compute_all_amount,
                            store=True, readonly=True,
                            digits=dp.get_precision('Amount'),
                            help=u'含税单价 乘以 数量')
    note = fields.Char(u'备注',
                       help=u'本行备注')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
