# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016  开阖软件(<http://osbzr.com>).
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

from datetime import datetime
from openerp.osv import fields, osv


class money_order(osv.osv):
    _name = 'money.order'
    _description = u"收款单/付款单"

    TYPE_SELECTION = [
        ('payables', u'应付款'),
        ('receipts', u'应收款'),
    ]

    def create(self, cr, uid, vals, context=None):
        if not vals.get('name') and context.get('default_receipt'):
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'receipt_order', context=context) or ''
        if not vals.get('name') and context.get('default_payment'):
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'payment_order', context=context) or ''

        if context.get('default_payment'):
            vals.update({'type': 'payables'})
        if context.get('default_receipt'):
            vals.update({'type': 'receipts'})

        return super(money_order, self).create(cr, uid, vals, context=context)

    _columns = {
        'state': fields.selection([
            ('draft', u'未审核'),
            ('done', u'已审核'),
            ('cancel', u'已取消')
        ], u'状态', readonly=True, copy=False),
        'partner_id': fields.many2one('partner', u'业务伙伴', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date': fields.date(u'单据日期', readonly=True, states={'draft': [('readonly', False)]}),
        'name': fields.char(u'单据编号', copy=False, readonly=True),
        'note': fields.text(u'备注', readonly=True, states={'draft': [('readonly', False)]}),
        'discount_amount': fields.float(u'整单折扣', readonly=True, states={'draft': [('readonly', False)]}),
        'advance_payment': fields.float(u'本次预收款', readonly=True, states={'draft': [('readonly', False)]}),
        'line_ids': fields.one2many('money.order.line', 'money_id', u'收支单行', readonly=True, states={'draft': [('readonly', False)]}),
        'source_ids': fields.one2many('source.order.line', 'money_id', u'源单行', readonly=True, states={'draft': [('readonly', False)]}),
        'type': fields.selection(TYPE_SELECTION, u'应收款/应付款'),
    }

    _defaults = {
        'state': 'draft',
        'date': fields.date.context_today,
    }

    def button_select_source_order(self, cr, uid, ids, context=None):
        if not ids:
            return

        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'money', 'source_order_line_tree')
        line_ini = self.browse(cr, uid, ids[0], context=context)
        return {
            'name': u'选择源单',
            'view_mode': 'tree',
            'view_id': view_id,
            'view_type': 'tree',
            'res_model': 'source.order.line',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                #                 'payment_expected_currency': inv.currency_id.id,
            }
        }

    def money_approve(self, cr, uid, ids, context=None):
        '''对收支单的提交审核按钮，还需修改'''
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True

    def money_action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def print_money_order(self, cr, uid, ids, context=None):
        return True


class money_order_line(osv.osv):
    _name = 'money.order.line'
    _description = u'收支单明细'

    _columns = {
        'state': fields.selection([
            ('draft', u'未审核'),
            ('done', u'已审核'),
            ('cancel', u'已取消')
        ], u'状态', readonly=True, copy=False),
        'money_id': fields.many2one('money.order', u'收款单'),
        'bank_id': fields.many2one('bank.account', u'结算账户'),
        'receipt_amount': fields.float(u'收款金额'),
        'payment_amount': fields.float(u'付款金额'),
        'mode_id': fields.many2one('settle.mode', u'结算方式'),
        'number': fields.char(u'结算号'),
        'note': fields.char(u'备注'),
    }


class money_invoice(osv.osv):
    _name = 'money.invoice'
    _description = u'源单'

    _columns = {
        'name': fields.char(u'订单编号', copy=False),
        'type': fields.char(u'源单类型'),
        'business_type': fields.char(u'业务类别'),
        'date': fields.date(u'单据日期'),
        'amount': fields.float(u'单据金额'),
        'reconciled': fields.float(u'已核销金额'),
        'to_reconcile': fields.float(u'未核销金额'),
    }


class source_order_line(osv.osv):
    _name = 'source.order.line'
    _description = u'源单明细'

    _columns = {
        'state': fields.selection([
            ('draft', u'未审核'),
            ('done', u'已审核'),
            ('cancel', u'已取消')
        ], u'状态', readonly=True, copy=False),
        'money_id': fields.many2one('money.order', u'收款单'),
        'name': fields.many2one('money.invoice', u'源单编号', copy=False),
        'business_type': fields.char(u'业务类别'),
        'date': fields.date(u'单据日期'),
        'amount': fields.float(u'单据金额'),
        'reconciled': fields.float(u'已核销金额'),
        'to_reconcile': fields.float(u'未核销金额'),
        'this_reconcile': fields.float(u'本次核销金额'),
    }


class other_money_order(osv.osv):
    _name = 'other.money.order'
    _description = u'其他应收款/应付款'

    TYPE_SELECTION = [
        ('other_payables', u'其他应付款'),
        ('other_receipts', u'其他应收款'),
    ]

    _columns = {
        'state': fields.selection([
            ('draft', u'未审核'),
            ('done', u'已审核'),
            ('cancel', u'已取消')
        ], u'状态', readonly=True, copy=False),
        'partner_id': fields.many2one('partner', u'业务伙伴', required=True),
        'name': fields.char(u'单据编号', copy=False),
        'date': fields.date(u'单据日期'),
        'total_amount': fields.float(u'应付金额/应收金额'),
        'bank_id': fields.many2one('bank.account', u'结算账户'),
        'line_ids': fields.one2many('other.money.order.line', 'other_money_id', u'收支单行'),
        'type': fields.selection(TYPE_SELECTION, u'其他应收款/应付款'),
    }

    def print_other_money_order(self, cr, uid, ids, context=None):
        '''打印 其他收入/支出单'''
        assert len(ids) == 1, '一次执行只能有一个id'
        return self.pool['report'].get_action(cr, uid, ids, 'money.report_other_money_order', context=context)


class other_money_order_line(osv.osv):
    _name = 'other.money.order.line'
    _description = u'其他应收应付明细'

    _columns = {
        'other_money_id': fields.many2one('other.money.order', u'其他收入/支出'),
        'other_money_type': fields.char(u'支出类别/收入类别'),
        'amount': fields.float(u'金额'),
        'note': fields.char(u'备注'),
    }
