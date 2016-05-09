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

from openerp import fields, models, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm

# 购货订单审核状态可选值
BUY_ORDER_STATES = [
        ('draft', u'未审核'),
        ('done', u'已审核'),
    ]

# 字段只读状态
READONLY_STATES = {
        'done': [('readonly', True)],
    }


class buy_order(models.Model):
    _name = "buy.order"
    _inherit = ['mail.thread']
    _description = u"购货订单"
    _order = 'date desc, id desc'

    @api.one
    @api.depends('line_ids.subtotal', 'discount_amount')
    def _compute_amount(self):
        '''当订单行和优惠金额改变时，改变优惠后金额'''
        total = sum(line.subtotal for line in self.line_ids)
        self.amount = total - self.discount_amount

    @api.one
    @api.depends('line_ids.quantity', 'line_ids.quantity_in')
    def _get_buy_goods_state(self):
        '''返回收货状态'''
        for line in self.line_ids:
            if line.quantity_in == 0:
                self.goods_state = u'未入库'
            elif line.quantity > line.quantity_in:
                self.goods_state = u'部分入库'
                break
            elif line.quantity == line.quantity_in:
                self.goods_state = u'全部入库'

    @api.model
    def _default_warehouse_dest(self):
        if self.env.context.get('warehouse_dest_type'):
            return self.env['warehouse'].get_warehouse_by_type(
                        self.env.context.get('warehouse_dest_type'))

        return self.env['warehouse'].browse()

    partner_id = fields.Many2one('partner', u'供应商', states=READONLY_STATES,
                                 ondelete='restrict')
    date = fields.Date(u'单据日期', states=READONLY_STATES,
                       default=lambda self: fields.Date.context_today(self),
                       select=True, copy=False, help=u"默认是订单创建日期")
    planned_date = fields.Date(
                        u'要求交货日期', states=READONLY_STATES,
                        default=lambda self: fields.Date.context_today(self),
                        select=True, copy=False, help=u"订单的要求交货日期")
    name = fields.Char(u'单据编号', select=True, copy=False,
                       help=u"购货订单的唯一编号，当创建时它会自动生成下一个编号。")
    type = fields.Selection([('buy', u'购货'), ('return', u'退货')], u'类型',
                            default='buy', states=READONLY_STATES)
    warehouse_dest_id = fields.Many2one('warehouse', u'调入仓库',
                                        default=_default_warehouse_dest,
                                        ondelete='restrict')
    line_ids = fields.One2many('buy.order.line', 'order_id', u'购货订单行',
                               states=READONLY_STATES, copy=True)
    note = fields.Text(u'备注')
    discount_rate = fields.Float(u'优惠率(%)', states=READONLY_STATES,
                                 digits_compute=dp.get_precision('Amount'))
    discount_amount = fields.Float(u'优惠金额', states=READONLY_STATES,
                                   track_visibility='always',
                                   digits_compute=dp.get_precision('Amount'))
    amount = fields.Float(u'优惠后金额', store=True, readonly=True,
                          compute='_compute_amount', track_visibility='always',
                          digits_compute=dp.get_precision('Amount'))
    prepayment = fields.Float(u'预付款', states=READONLY_STATES,
                           digits_compute=dp.get_precision('Amount'))
    bank_account_id = fields.Many2one('bank.account', u'结算账户',
                                      ondelete='restrict')
    approve_uid = fields.Many2one('res.users', u'审核人',
                                  copy=False, ondelete='restrict')
    state = fields.Selection(BUY_ORDER_STATES, u'审核状态', readonly=True,
                             help=u"购货订单的审核状态", select=True, copy=False,
                             default='draft')
    goods_state = fields.Char(u'收货状态', compute=_get_buy_goods_state,
                              default=u'未入库', store=True,
                              help=u"购货订单的收货状态", select=True, copy=False)
    cancelled = fields.Boolean(u'已终止')

    @api.one
    @api.onchange('discount_rate', 'line_ids')
    def onchange_discount_rate(self):
        '''当优惠率或购货订单行发生变化时，单据优惠金额发生变化'''
        total = sum(line.subtotal for line in self.line_ids)
        self.discount_amount = total * self.discount_rate * 0.01


    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise except_orm(u'错误', u'不能删除已审核的单据')

        return super(buy_order, self).unlink()

    @api.one
    def generate_payment_order(self):
        '''由购货订单生成付款单'''
        # 入库单/退货单
        if self.type == 'buy':
            amount = self.amount
            this_reconcile = self.prepayment
        else:
            amount = - self.amount
            this_reconcile = - self.prepayment
        if self.prepayment:
            money_lines = []
            money_lines.append({
                'bank_id': self.bank_account_id.id,
                'amount': this_reconcile,
            })

            rec = self.with_context(type='pay')
            money_order = rec.env['money.order'].create({
                                'partner_id': self.partner_id.id,
                                'date': fields.Date.context_today(self),
                                'line_ids':
                                [(0, 0, line) for line in money_lines],
                                'type': 'pay',
                                'amount': amount,
                                'reconciled': this_reconcile,
                                'to_reconcile': amount,
                                'state': 'draft',
                            })
            money_order.money_order_done()

    @api.one
    def buy_order_done(self):
        '''审核购货订单'''
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        if not self.line_ids:
            raise except_orm(u'错误', u'请输入产品明细行！')
        for line in self.line_ids:
            if line.quantity == 0:
                raise except_orm(u'错误', u'请输入产品数量！')
        if self.bank_account_id and not self.prepayment:
            raise except_orm(u'警告！', u'结算账户不为空时，需要输入预付款！')
        if not self.bank_account_id and self.prepayment:
            raise except_orm(u'警告！', u'预付款不为空时，请选择结算账户！')
        # 采购预付款生成付款单
        self.generate_payment_order()
        self.buy_generate_receipt()
        self.state = 'done'
        self.approve_uid = self._uid

    @api.one
    def buy_order_draft(self):
        '''反审核购货订单'''
        if self.state == 'draft':
            raise except_orm(u'错误', u'请不要重复反审核！')
        if self.goods_state != u'未入库':
            raise except_orm(u'错误', u'该购货订单已经收货，不能反审核！')
        else:
            # 查找产生的入库单并删除
            receipt = self.env['buy.receipt'].search(
                             [('order_id', '=', self.name)])
            if receipt:
                receipt.unlink()
        self.state = 'draft'
        self.approve_uid = ''

    @api.one
    def get_receipt_line(self, line, single=False):
        # TODO：如果退货，warehouse_dest_id，warehouse_id要调换
        qty = 0
        discount_amount = 0
        if single:
            qty = 1
            discount_amount = (line.discount_amount /
                               (line.quantity - line.quantity_in))
        else:
            qty = line.quantity - line.quantity_in
            discount_amount = line.discount_amount
        if self.type == 'buy':
            warehouse_id = line.warehouse_id.id
            warehouse_dest_id = line.warehouse_dest_id.id
        # 如果退货，调换warehouse_dest_id，warehouse_id
        elif self.type == 'return':
            warehouse_id = line.warehouse_dest_id.id
            warehouse_dest_id = line.warehouse_id.id
        return {
                    'buy_line_id': line.id,
                    'goods_id': line.goods_id.id,
                    'attribute_id': line.attribute_id.id,
                    'uom_id': line.uom_id.id,
                    'warehouse_id': warehouse_id,
                    'warehouse_dest_id': warehouse_dest_id,
                    'goods_qty': qty,
                    'cost_unit': line.price,
                    'price': line.price,
                    'discount_rate': line.discount_rate,
                    'discount_amount': discount_amount,
                    'tax_rate': line.tax_rate,
                    'note': line.note or '',
                }

    @api.one
    def buy_generate_receipt(self):
        '''由购货订单生成采购入库单'''
        receipt_line = []  # 采购入库单行

        for line in self.line_ids:
            # 如果订单部分入库，则点击此按钮时生成剩余数量的入库单
            to_in = line.quantity - line.quantity_in
            if to_in == 0:
                continue
            if line.goods_id.force_batch_one:
                i = 0
                while i < to_in:
                    i += 1
                    receipt_line.append(
                                self.get_receipt_line(line, single=True))
            else:
                receipt_line.append(self.get_receipt_line(line, single=False))

        if not receipt_line:
            return {}
        if self.type == 'buy':
            receipt_id = self.env['buy.receipt'].create({
                                'partner_id': self.partner_id.id,
                                'date': self.planned_date,
                                'order_id': self.id,
                                'line_in_ids': [
                                    (0, 0, line[0]) for line in receipt_line],
                                'origin': 'buy.receipt',
                                'note': self.note,
                                'discount_rate': self.discount_rate,
                                'discount_amount': self.discount_amount,
                            })
            view_id = self.env.ref('buy.buy_receipt_form').id
            name = u'采购入库单'
        elif self.type == 'return':
            rec = self.with_context(is_return=True)
            receipt_id = rec.env['buy.receipt'].create({
                            'partner_id': self.partner_id.id,
                            'date': self.planned_date,
                            'order_id': self.id,
                            'line_out_ids': [
                                (0, 0, line[0]) for line in receipt_line],
                            'note': self.note,
                            'discount_rate': self.discount_rate,
                            'discount_amount': self.discount_amount,
                        })
            view_id = self.env.ref('buy.buy_return_form').id
            name = u'采购退货单'
        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view_id, 'form')],
            'res_model': 'buy.receipt',
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', receipt_id)],
            'target': 'current',
        }


class buy_order_line(models.Model):
    _name = 'buy.order.line'
    _description = u'购货订单明细'

    @api.one
    @api.depends('goods_id')
    def _compute_using_attribute(self):
        '''返回订单行中产品是否使用属性'''
        self.using_attribute = self.goods_id.attribute_ids and True or False

    @api.model
    def _default_warehouse(self):
        context = self._context or {}
        if context.get('warehouse_type'):
            return self.env['warehouse'].get_warehouse_by_type(
                                            context.get('warehouse_type'))
        return False

    @api.one
    @api.depends('quantity', 'price', 'discount_amount', 'tax_rate')
    def _compute_all_amount(self):
        '''当订单行的数量、单价、折扣额、税率改变时，改变购货金额、税额、价税合计'''
        amount = self.quantity * self.price - self.discount_amount  # 折扣后金额
        tax_amt = amount * self.tax_rate * 0.01  # 税额
        self.price_taxed = self.price * (1 + self.tax_rate * 0.01)
        self.amount = amount
        self.tax_amount = tax_amt
        self.subtotal = amount + tax_amt

    order_id = fields.Many2one('buy.order', u'订单编号', select=True,
                               required=True, ondelete='cascade')
    goods_id = fields.Many2one('goods', u'商品', ondelete='restrict')
    using_attribute = fields.Boolean(u'使用属性', compute=_compute_using_attribute)
    attribute_id = fields.Many2one('attribute', u'属性',
                                   ondelete='restrict',
                                   domain="[('goods_id', '=', goods_id)]")
    uom_id = fields.Many2one('uom', u'单位', ondelete='restrict')
    warehouse_id = fields.Many2one('warehouse', u'调出仓库',
                                   ondelete='restrict',
                                   default=_default_warehouse)
    warehouse_dest_id = fields.Many2one('warehouse',
                                        u'仓库', ondelete='restrict')
    quantity = fields.Float(u'数量', default=1,
                            digits_compute=dp.get_precision('Quantity'))
    quantity_in = fields.Float(u'已入库数量', copy=False,
                               digits_compute=dp.get_precision('Quantity'))
    price = fields.Float(u'购货单价',
                         digits_compute=dp.get_precision('Amount'))
    price_taxed = fields.Float(u'含税单价', compute=_compute_all_amount,
                               store=True, readonly=True,
                               digits_compute=dp.get_precision('Amount'))
    discount_rate = fields.Float(u'折扣率%')
    discount_amount = fields.Float(u'折扣额',
                                   digits_compute=dp.get_precision('Amount'))
    amount = fields.Float(u'金额', compute=_compute_all_amount,
                          store=True, readonly=True,
                          digits_compute=dp.get_precision('Amount'))
    tax_rate = fields.Float(u'税率(%)', default=17.0)
    tax_amount = fields.Float(u'税额', compute=_compute_all_amount,
                              store=True, readonly=True,
                              digits_compute=dp.get_precision('Amount'))
    subtotal = fields.Float(u'价税合计', compute=_compute_all_amount,
                            store=True, readonly=True,
                            digits_compute=dp.get_precision('Amount'))
    note = fields.Char(u'备注')
    # TODO:放到单独模块中 sell_to_buy many2one 到sell.order
    origin = fields.Char(u'销售单号')

    @api.one
    @api.onchange('goods_id')
    def onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的单位、默认仓库、成本价'''
        if self.goods_id:
            self.uom_id = self.goods_id.uom_id
            if not self.goods_id.cost:
                raise except_orm(u'错误', u'请先设置商品的成本！')
            self.price = self.goods_id.cost

    @api.one
    @api.onchange('quantity', 'price', 'discount_rate')
    def onchange_discount_rate(self):
        '''当数量、单价或优惠率发生变化时，优惠金额发生变化'''
        self.discount_amount = (self.quantity * self.price *
                                self.discount_rate * 0.01)


class buy_receipt(models.Model):
    _name = "buy.receipt"
    _inherits = {'wh.move': 'buy_move_id'}
    _inherit = ['mail.thread']
    _description = u"采购入库单"
    _order = 'date desc, id desc'

    @api.one
    @api.depends('line_in_ids.subtotal', 'discount_amount',
                 'payment', 'line_out_ids.subtotal')
    def _compute_all_amount(self):
        '''当优惠金额改变时，改变优惠后金额和本次欠款'''
        total = 0
        if self.line_in_ids:
            # 入库时优惠前总金额
            total = sum(line.subtotal for line in self.line_in_ids)
        elif self.line_out_ids:
            # 退货时优惠前总金额
            total = sum(line.subtotal for line in self.line_out_ids)
        self.amount = total - self.discount_amount
        self.debt = self.amount - self.payment

    @api.one
    @api.depends('is_return', 'invoice_id.reconciled', 'invoice_id.amount')
    def _get_buy_money_state(self):
        '''返回付款状态'''
        if not self.is_return:
            if self.invoice_id.reconciled == 0:
                self.money_state = u'未付款'
            elif self.invoice_id.reconciled < self.invoice_id.amount:
                self.money_state = u'部分付款'
            elif self.invoice_id.reconciled == self.invoice_id.amount:
                self.money_state = u'全部付款'

    @api.one
    @api.depends('is_return', 'invoice_id.reconciled', 'invoice_id.amount')
    def _get_buy_return_state(self):
        '''返回退款状态'''
        if self.is_return:
            if self.invoice_id.reconciled == 0:
                self.return_state = u'未退款'
            elif abs(self.invoice_id.reconciled) < abs(self.invoice_id.amount):
                self.return_state = u'部分退款'
            elif self.invoice_id.reconciled == self.invoice_id.amount:
                self.return_state = u'全部退款'

    buy_move_id = fields.Many2one('wh.move', u'入库单',
                                  required=True, ondelete='cascade')
    is_return = fields.Boolean(u'是否退货',
                    default=lambda self: self.env.context.get('is_return'))
    order_id = fields.Many2one('buy.order', u'源单号',
                               copy=False, ondelete='cascade')
    invoice_id = fields.Many2one('money.invoice', u'发票号', copy=False,
                                 ondelete='restrict')
    date_due = fields.Date(u'到期日期', copy=False)
    discount_rate = fields.Float(u'优惠率(%)', states=READONLY_STATES)
    discount_amount = fields.Float(u'优惠金额', states=READONLY_STATES,
                                   digits_compute=dp.get_precision('Amount'))
    amount = fields.Float(u'优惠后金额', compute=_compute_all_amount,
                          store=True, readonly=True,
                          digits_compute=dp.get_precision('Amount'))
    payment = fields.Float(u'本次付款', states=READONLY_STATES,
                           digits_compute=dp.get_precision('Amount'))
    bank_account_id = fields.Many2one('bank.account', u'结算账户', 
                                      ondelete='restrict')
    debt = fields.Float(u'本次欠款', compute=_compute_all_amount,
                        store=True, readonly=True, copy=False,
                        digits_compute=dp.get_precision('Amount'))
    cost_line_ids = fields.One2many('cost.line', 'buy_id', u'采购费用', copy=False)
    money_state = fields.Char(u'付款状态', compute=_get_buy_money_state,
                              store=True, default=u'未付款',
                              help=u"采购入库单的付款状态",
                              select=True, copy=False)
    return_state = fields.Char(u'退款状态', compute=_get_buy_return_state,
                               store=True, default=u'未退款',
                               help=u"采购退货单的退款状态",
                               select=True, copy=False)

    @api.one
    @api.onchange('discount_rate', 'line_in_ids', 'line_out_ids')
    def onchange_discount_rate(self):
        '''当优惠率或订单行发生变化时，单据优惠金额发生变化'''
        total = 0
        if self.line_in_ids:
            # 入库时优惠前总金额
            total = sum(line.subtotal for line in self.line_in_ids)
        elif self.line_out_ids:
            # 退货时优惠前总金额
            total = sum(line.subtotal for line in self.line_out_ids)
        if self.discount_rate:
            self.discount_amount = total * self.discount_rate * 0.01

    def get_move_origin(self, vals):
        return self._name + (self.env.context.get('is_return') and
                             '.return' or '.buy')

    @api.model
    def create(self, vals):
        '''创建采购入库单时生成有序编号'''
        if not self.env.context.get('is_return'):
            name = self._name
        else:
            name = 'buy.return'
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get(name) or '/'

        vals.update({
            'origin': self.get_move_origin(vals)
        })
        return super(buy_receipt, self).create(vals)

    @api.multi
    def unlink(self):
        for receipt in self:
            if receipt.state == 'done':
                raise except_orm(u'错误', u'不能删除已审核的单据')
            move = self.env['wh.move'].search([
                ('id', '=', receipt.buy_move_id.id)
            ])
            if move:
                move.unlink()

        return super(buy_receipt, self).unlink()

    @api.one
    def buy_receipt_done(self):
        '''审核采购入库单/退货单，更新本单的付款状态/退款状态，并生成源单和付款单'''
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        for line in self.line_in_ids:
            if line.goods_qty == 0:
                raise except_orm(u'错误', u'请输入产品数量！')
        for line in self.line_out_ids:
            if line.goods_qty == 0:
                raise except_orm(u'错误', u'请输入产品数量！')
        if self.bank_account_id and not self.payment:
            raise except_orm(u'警告！', u'结算账户不为空时，需要输入付款额！')
        if not self.bank_account_id and self.payment:
            raise except_orm(u'警告！', u'付款额不为空时，请选择结算账户！')
        if self.payment > self.amount:
            raise except_orm(u'警告！', u'本次付款金额不能大于折后金额！')

        if (sum(cost_line.amount for cost_line in self.cost_line_ids) !=
                sum(line.share_cost for line in self.line_in_ids)):
            raise except_orm(u'警告！', u'采购费用还未分摊或分摊不正确！')

        if self.order_id:
            if not self.is_return:
                line_ids = self.line_in_ids
            else:
                line_ids = self.line_out_ids
            for line in line_ids:
                line.buy_line_id.quantity_in += line.goods_qty

        # 入库单/退货单 生成源单
        if not self.is_return:
            amount = self.amount
            this_reconcile = self.payment
        else:
            amount = -self.amount
            this_reconcile = -self.payment
        categ = self.env.ref('money.core_category_purchase')
        source_id = self.env['money.invoice'].create({
                            'move_id': self.buy_move_id.id,
                            'name': self.name,
                            'partner_id': self.partner_id.id,
                            'category_id': categ.id,
                            'date': fields.Date.context_today(self),
                            'amount': amount,
                            'reconciled': 0,
                            'to_reconcile': amount,
                            'date_due': self.date_due,
                            'state': 'draft',
                        })
        self.invoice_id = source_id.id
        # 采购费用产生源单
        if sum(cost_line.amount for cost_line in self.cost_line_ids) > 0:
            for line in self.cost_line_ids:
                cost_id = self.env['money.invoice'].create({
                            'move_id': self.buy_move_id.id,
                            'name': self.name,
                            'partner_id': line.partner_id.id,
                            'category_id': line.category_id.id,
                            'date': fields.Date.context_today(self),
                            'amount': line.amount,
                            'reconciled': 0.0,
                            'to_reconcile': line.amount,
                            'date_due': self.date_due,
                            'state': 'draft',
                        })
        # 生成付款单
        if self.payment:
            money_lines = []
            source_lines = []
            money_lines.append({
                'bank_id': self.bank_account_id.id,
                'amount': this_reconcile,
            })
            source_lines.append({
                'name': source_id.id,
                'category_id': categ.id,
                'date': source_id.date,
                'amount': amount,
                'reconciled': 0.0,
                'to_reconcile': amount,
                'this_reconcile': this_reconcile,
            })

            rec = self.with_context(type='pay')
            money_order = rec.env['money.order'].create({
                                'partner_id': self.partner_id.id,
                                'date': fields.Date.context_today(self),
                                'line_ids':
                                [(0, 0, line) for line in money_lines],
                                'source_ids':
                                [(0, 0, line) for line in source_lines],
                                'type': 'pay',
                                'amount': amount,
                                'reconciled': this_reconcile,
                                'to_reconcile': amount,
                                'state': 'draft',
                            })
            money_order.money_order_done()
        # 调用wh.move中审核方法，更新审核人和审核状态
        self.buy_move_id.approve_order()
        # 生成分拆单 FIXME:无法跳转到新生成的分单
        if self.order_id:
            return self.order_id.buy_generate_receipt()

    @api.one
    def buy_share_cost(self):
        '''入库单上的采购费用分摊到入库单明细行上'''
        total_amount = 0
        for line in self.line_in_ids:
            total_amount += line.amount
        for line in self.line_in_ids:
            cost = sum(cost_line.amount for cost_line in self.cost_line_ids)
            line.share_cost = cost / total_amount * line.amount
        return True


class wh_move_line(models.Model):
    _inherit = 'wh.move.line'
    _description = u"采购入库明细"

    buy_line_id = fields.Many2one('buy.order.line',
                                  u'购货单行', ondelete='cascade')
    share_cost = fields.Float(u'采购费用',
                              digits_compute=dp.get_precision('Amount'))

    @api.multi
    @api.onchange('goods_id')
    def onchange_goods_id(self):
        if self.goods_id:
            partner_id = self.env.context.get('default_partner')
            partner = self.env['partner'].search([('id', '=', partner_id)])
            is_return = self.env.context.get('default_is_return')
            if self.type == 'in':
                if not self.goods_id.cost:
                    raise except_orm(u'错误', u'请先设置商品的成本！')
                self.price = self.goods_id.cost
                # 如果是销售退货单行
                if is_return:
                    matched = False # 在商品的价格清单中是否找到匹配的价格
                    for line in self.goods_id.price_ids:
                        if partner.c_category_id == line.category_id:
                            self.price = line.price
                            matched = True
                    if not matched:
                        raise except_orm(u'错误', u'请先设置商品的价格清单或客户类别！')
            elif self.type == 'out':
                self.warehouse_id = self.goods_id.default_wh  # 取产品的默认仓库
                matched = False # 在商品的价格清单中是否找到匹配的价格
                for line in self.goods_id.price_ids:
                    if partner.c_category_id == line.category_id:
                        self.price = line.price
                        matched = True
                # 如果是采购退货单行
                if is_return:
                    if not self.goods_id.cost:
                        raise except_orm(u'错误', u'请先设置商品的成本！')
                    self.price = self.goods_id.cost
                    matched = True

                if not matched:
                    raise except_orm(u'错误', u'请先设置商品的价格清单或客户类别！')

        return super(wh_move_line,self).onchange_goods_id()



class cost_line(models.Model):
    _inherit = 'cost.line'

    buy_id = fields.Many2one('buy.receipt', u'入库单号', ondelete='cascade')


class money_invoice(models.Model):
    _inherit = 'money.invoice'

    move_id = fields.Many2one('wh.move', string=u'出入库单',
                              readonly=True, ondelete='cascade')

