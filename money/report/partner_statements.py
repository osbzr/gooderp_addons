# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp import fields, models, api, tools

class partner_statements_report_with_goods(models.TransientModel):
    _name = "partner.statements.report.with.goods"
    _description = u"业务伙伴对账单带商品明细"

    partner_id = fields.Many2one('partner', string=u'业务伙伴', readonly=True)
    name = fields.Char(string=u'单据编号', readonly=True)
    date = fields.Date(string=u'单据日期', readonly=True)
    category_id = fields.Many2one('core.category', u'商品类别')
    goods_code = fields.Char(u'商品编号')
    goods_name = fields.Char(u'商品名称')
    attribute_id = fields.Many2one('attribute', u'规格型号')
    uom_id = fields.Many2one('uom', u'单位')
    quantity = fields.Float(u'数量')
    price = fields.Float(u'单价')
    discount_amount = fields.Float(u'折扣额')
    without_tax_amount = fields.Float(u'不含税金额')
    tax_amount = fields.Float(u'税额')
    order_amount = fields.Float(string=u'订单金额', readonly=True) # 采购、销售
    benefit_amount = fields.Float(string=u'优惠金额', readonly=True)
    fee = fields.Float(string=u'客户承担费用', readonly=True)
    amount = fields.Float(string=u'应收金额', readonly=True)
    pay_amount = fields.Float(string=u'付款金额', readonly=True)
    balance_amount = fields.Float(string=u'应收款余额', readonly=True)
    note = fields.Char(string=u'备注', readonly=True)
    move_id = fields.Many2one('wh.move', string=u'出入库单', readonly=True)

    @api.multi
    def find_source_order(self):
        # 客户、供应商
        if self._context['is_customer']:
            # 查看源单，两种情况：收款单、销售发货单
            money = self.env['money.order'].search([('name', '=', self.name)])
            if money: # 收款单
                view = self.env.ref('money.money_order_form')
                return {
                    'name': u'收款单',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': False,
                    'views': [(view.id, 'form')],
                    'res_model': 'money.order',
                    'type': 'ir.actions.act_window',
                    'res_id': money.id,
                    'context': {'type': 'get'}
                }

            # 销售发货单
            delivery = self.env['sell.delivery'].search([('name', '=', self.name)])
            view = self.env.ref('sell.sell_delivery_form')
            return {
                'name': u'销售发货单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'sell.delivery',
                'type': 'ir.actions.act_window',
                'res_id': delivery.id,
                'context': {'type': 'get'}
            }
        else:
            # 查看源单，两种情况：付款单、采购入库单
            money = self.env['money.order'].search([('name', '=', self.name)])
            if money: # 付款单
                view = self.env.ref('money.money_order_form')
                return {
                    'name': u'付款单',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': False,
                    'views': [(view.id, 'form')],
                    'res_model': 'money.order',
                    'type': 'ir.actions.act_window',
                    'res_id': money.id,
                    'context': {'type': 'pay'}
                }

            # 采购入库单
            buy = self.env['buy.receipt'].search([('name', '=', self.name)])
            view = self.env.ref('buy.buy_receipt_form')
            return {
                'name': u'采购入库单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'buy.receipt',
                'type': 'ir.actions.act_window',
                'res_id': buy.id,
                'context': {'type': 'pay'}
            }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
