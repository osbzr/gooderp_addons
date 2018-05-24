# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import fields, models, api


class SellReceipt(models.TransientModel):
    _name = 'sell.receipt'
    _description = u'销售收款一览表'

    c_category_id = fields.Many2one('core.category', u'客户类别')
    partner_id = fields.Many2one('partner', u'客户')
    user_id = fields.Many2one('res.users', u'销售员')
    type = fields.Char(u'业务类别')
    date = fields.Date(u'单据日期')
    warehouse_id = fields.Many2one('warehouse', u'仓库')
    order_name = fields.Char(u'单据编号')
    sell_amount = fields.Float(u'销售金额', digits=dp.get_precision('Amount'))
    discount_amount = fields.Float(u'优惠金额',
                                   digits=dp.get_precision('Amount'))
    amount = fields.Float(u'成交金额', digits=dp.get_precision('Amount'))
    partner_cost = fields.Float(u'客户承担费用', digits=dp.get_precision('Amount'))
    receipt = fields.Float(u'已收款', digits=dp.get_precision('Amount'))
    balance = fields.Float(u'应收款余额', digits=dp.get_precision('Amount'))
    receipt_rate = fields.Float(u'回款率(%)')
    note = fields.Char(u'备注')

    @api.multi
    def view_detail(self):
        '''销售收款一览表查看明细按钮'''
        self.ensure_one()
        order = self.env['sell.delivery'].search(
            [('name', '=', self.order_name)])
        if order:
            if not order.is_return:
                view = self.env.ref('sell.sell_delivery_form')
            else:
                view = self.env.ref('sell.sell_return_form')

            return {
                'name': u'销售发货单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'sell.delivery',
                'type': 'ir.actions.act_window',
                'res_id': order.id,
            }

    @api.multi
    def generate_reconcile_order(self):
        """新建核销单，应收冲预收，客户为所选行客户"""
        self.ensure_one()
        view = self.env.ref('money.reconcile_order_form')
        # 如果已存在该客户核销单，则查看核销单，否则创建
        order = self.env['reconcile.order'].search([
            ('partner_id', '=', self.partner_id.id),
            ('business_type', '=', 'adv_pay_to_get')])
        if order:
            return {
                'name': u'核销单',
                'view_mode': 'form',
                'views': [(view.id, 'form')],
                'res_model': 'reconcile.order',
                'type': 'ir.actions.act_window',
                'res_id': order.id,
            }

        order = self.env['reconcile.order'].create({
            'partner_id': self.partner_id.id,
            'business_type': 'adv_pay_to_get',
        })
        order.onchange_partner_id()
        return {
            'name': u'核销单',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'res_model': 'reconcile.order',
            'type': 'ir.actions.act_window',
            'res_id': order.id,
        }
