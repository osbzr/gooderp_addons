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
BUY_ORDER_STATES = [
    ('draft', u'未审核'),
    ('done', u'已审核'),
    ('cancel', u'已作废')]

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
}


class BuyOrder(models.Model):
    _name = "buy.order"
    _inherit = ['mail.thread']
    _description = u"购货订单"
    _order = 'date desc, id desc'

    @api.one
    @api.depends('line_ids.subtotal', 'discount_amount')
    def _compute_amount(self):
        '''当订单行和优惠金额改变时，改变成交金额'''
        total = sum(line.subtotal for line in self.line_ids)
        self.amount = total - self.discount_amount

    @api.one
    @api.depends('line_ids.quantity', 'line_ids.quantity_in')
    def _get_buy_goods_state(self):
        '''返回收货状态'''
        if all(line.quantity_in == 0 for line in self.line_ids):
            self.goods_state = u'未入库'
        elif any(line.quantity > line.quantity_in for line in self.line_ids):
            self.goods_state = u'部分入库'
        else:
            self.goods_state = u'全部入库'

    @api.model
    def _default_warehouse_dest_impl(self):
        if self.env.context.get('warehouse_dest_type'):
            return self.env['warehouse'].get_warehouse_by_type(
                self.env.context.get('warehouse_dest_type'))

    @api.model
    def _default_warehouse_dest(self):
        '''获取默认调入仓库'''
        return self._default_warehouse_dest_impl()

    @api.one
    def _get_paid_amount(self):
        '''计算购货订单付款/退款状态'''
        receipts = self.env['buy.receipt'].search([('order_id', '=', self.id)])
        money_order_rows = self.env['money.order'].search([('buy_id', '=', self.id),
                                                           ('reconciled', '=', 0),
                                                           ('state', '=', 'done')])
        self.paid_amount = sum([receipt.invoice_id.reconciled for receipt in receipts]) +\
            sum([order_row.amount for order_row in money_order_rows])

    @api.depends('receipt_ids')
    def _compute_receipt(self):
        for order in self:
            order.receipt_count = len(order.receipt_ids.ids)

    @api.depends('receipt_ids')
    def _compute_invoice(self):
        for order in self:
            order.invoice_ids = order.receipt_ids.mapped('invoice_id')
            order.invoice_count = len(order.invoice_ids.ids)

    @api.one
    @api.depends('partner_id')
    def _compute_currency_id(self):
        """
        计算货币
        :return:
        """
        self.currency_id = self.partner_id.s_category_id.account_id.currency_id.id or self.partner_id.c_category_id.account_id.currency_id.id

    partner_id = fields.Many2one('partner', u'供应商',
                                 states=READONLY_STATES,
                                 ondelete='restrict',
                                 help=u'供应商')
    date = fields.Date(u'单据日期',
                       states=READONLY_STATES,
                       default=lambda self: fields.Date.context_today(self),
                       index=True,
                       copy=False,
                       help=u"默认是订单创建日期")
    planned_date = fields.Date(
        u'要求交货日期',
        states=READONLY_STATES,
        default=lambda self: fields.Date.context_today(
            self),
        index=True,
        copy=False,
        help=u"订单的要求交货日期")
    name = fields.Char(u'单据编号',
                       index=True,
                       copy=False,
                       help=u"购货订单的唯一编号，当创建时它会自动生成下一个编号。")
    type = fields.Selection([('buy', u'购货'),
                             ('return', u'退货')],
                            u'类型',
                            default='buy',
                            states=READONLY_STATES,
                            help=u'购货订单的类型，分为购货或退货')
    ref = fields.Char(u'供应商订单号')
    warehouse_dest_id = fields.Many2one('warehouse',
                                        u'调入仓库',
                                        required=True,
                                        default=_default_warehouse_dest,
                                        ondelete='restrict',
                                        states=READONLY_STATES,
                                        help=u'将商品调入到该仓库')
    invoice_by_receipt = fields.Boolean(string=u"按收货结算",
                                        default=True,
                                        help=u'如未勾选此项，可在资金行里输入付款金额，订单保存后，采购人员可以单击资金行上的【确认】按钮。')
    line_ids = fields.One2many('buy.order.line',
                               'order_id',
                               u'购货订单行',
                               states=READONLY_STATES,
                               copy=True,
                               help=u'购货订单的明细行，不能为空')
    note = fields.Text(u'备注',
                       help=u'单据备注')
    discount_rate = fields.Float(u'优惠率(%)',
                                 states=READONLY_STATES,
                                 digits=dp.get_precision('Amount'),
                                 help=u'整单优惠率')
    discount_amount = fields.Float(u'抹零',
                                   states=READONLY_STATES,
                                   track_visibility='always',
                                   digits=dp.get_precision('Amount'),
                                   help=u'整单优惠金额，可由优惠率自动计算出来，也可手动输入')
    amount = fields.Float(u'成交金额',
                          store=True,
                          compute='_compute_amount',
                          track_visibility='always',
                          digits=dp.get_precision('Amount'),
                          help=u'总金额减去优惠金额')
    prepayment = fields.Float(u'预付款',
                              states=READONLY_STATES,
                              digits=dp.get_precision('Amount'),
                              help=u'输入预付款审核购货订单，会产生一张付款单')
    bank_account_id = fields.Many2one('bank.account',
                                      u'结算账户',
                                      ondelete='restrict',
                                      help=u'用来核算和监督企业与其他单位或个人之间的债权债务的结算情况')
    approve_uid = fields.Many2one('res.users',
                                  u'审核人',
                                  copy=False,
                                  ondelete='restrict',
                                  help=u'审核单据的人')
    state = fields.Selection(BUY_ORDER_STATES,
                             u'审核状态',
                             readonly=True,
                             help=u"购货订单的审核状态",
                             index=True,
                             copy=False,
                             default='draft')
    goods_state = fields.Char(u'收货状态',
                              compute=_get_buy_goods_state,
                              default=u'未入库',
                              store=True,
                              help=u"购货订单的收货状态",
                              index=True,
                              copy=False)
    cancelled = fields.Boolean(u'已终止',
                               help=u'该单据是否已终止')
    pay_ids = fields.One2many("payment.plan",
                              "buy_id",
                              string=u"付款计划",
                              help=u'分批付款时使用付款计划')
    goods_id = fields.Many2one(
        'goods', related='line_ids.goods_id', string=u'商品')
    receipt_ids = fields.One2many(
        'buy.receipt', 'order_id', string='Receptions', copy=False)
    receipt_count = fields.Integer(
        compute='_compute_receipt', string='Receptions Count', default=0)
    invoice_ids = fields.One2many(
        'money.invoice', compute='_compute_invoice', string='Invoices')
    invoice_count = fields.Integer(
        compute='_compute_invoice', string='Invoices Count', default=0)
    currency_id = fields.Many2one('res.currency',
                                  u'外币币别',
                                  compute='_compute_currency_id',
                                  store=True,
                                  help=u'外币币别')
    user_id = fields.Many2one(
        'res.users',
        u'经办人',
        ondelete='restrict',
        states=READONLY_STATES,
        default=lambda self: self.env.user,
        help=u'单据经办人',
    )
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    paid_amount = fields.Float(
        u'已付金额', compute=_get_paid_amount, readonly=True)

    @api.onchange('discount_rate', 'line_ids')
    def onchange_discount_rate(self):
        '''当优惠率或购货订单行发生变化时，单据优惠金额发生变化'''
        total = sum(line.subtotal for line in self.line_ids)
        self.discount_amount = total * self.discount_rate * 0.01

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            for line in self.line_ids:
                if line.goods_id.tax_rate and self.partner_id.tax_rate:
                    if line.goods_id.tax_rate >= self.partner_id.tax_rate:
                        line.tax_rate = self.partner_id.tax_rate
                    else:
                        line.tax_rate = line.goods_id.tax_rate
                elif line.goods_id.tax_rate and not self.partner_id.tax_rate:
                    line.tax_rate = line.goods_id.tax_rate
                elif not line.goods_id.tax_rate and self.partner_id.tax_rate:
                    line.tax_rate = self.partner_id.tax_rate
                else:
                    line.tax_rate = self.env.user.company_id.import_tax_rate

    def _get_vals(self):
        '''返回创建 money_order 时所需数据'''
        flag = (self.type == 'buy' and 1 or -1)  # 用来标志入库或退货
        amount = flag * self.amount
        this_reconcile = flag * self.prepayment
        money_lines = [{
            'bank_id': self.bank_account_id.id,
            'amount': this_reconcile,
        }]
        return {
            'partner_id': self.partner_id.id,
            'bank_name': self.partner_id.bank_name,
            'bank_num': self.partner_id.bank_num,
            'date': fields.Date.context_today(self),
            'line_ids':
            [(0, 0, line) for line in money_lines],
            'amount': amount,
            'reconciled': this_reconcile,
            'to_reconcile': amount,
            'state': 'draft',
            'origin_name': self.name,
            'buy_id': self.id,
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
    def buy_order_done(self):
        '''审核购货订单'''
        if self.state == 'done':
            raise UserError(u'请不要重复审核')
        if not self.line_ids:
            raise UserError(u'请输入商品明细行')
        for line in self.line_ids:
            if line.quantity <= 0 or line.price_taxed < 0:
                raise UserError(u'商品 %s 的数量和含税单价不能小于0' % line.goods_id.name)
            if line.tax_amount > 0 and self.currency_id:
                raise UserError(u'外贸免税')
        if not self.bank_account_id and self.prepayment:
            raise UserError(u'预付款不为空时，请选择结算账户')
        # 采购预付款生成付款单
        self.generate_payment_order()
        self.buy_generate_receipt()
        self.state = 'done'
        self.approve_uid = self._uid

    @api.one
    def buy_order_draft(self):
        '''反审核购货订单'''
        if self.state == 'draft':
            raise UserError(u'请不要重复反审核！')
        if self.goods_state != u'未入库':
            raise UserError(u'该购货订单已经收货，不能反审核！')
        # 查找产生的入库单并删除
        receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.name)])
        receipt.unlink()
        # 查找产生的付款单并反审核，删除
        money_order = self.env['money.order'].search(
            [('origin_name', '=', self.name)])
        if money_order:
            if money_order.state == 'done':
                money_order.money_order_draft()
            money_order.unlink()
        self.state = 'draft'
        self.approve_uid = ''

    @api.one
    def get_receipt_line(self, line, single=False):
        '''返回采购入库/退货单行'''
        qty = 0
        discount_amount = 0
        if single:
            qty = 1
            discount_amount = (line.discount_amount /
                               ((line.quantity - line.quantity_in) or 1))
        else:
            qty = line.quantity - line.quantity_in
            discount_amount = line.discount_amount
        return {
            'type': self.type == 'buy' and 'in' or 'out',
            'buy_line_id': line.id,
            'goods_id': line.goods_id.id,
            'attribute_id': line.attribute_id.id,
            'uos_id': line.goods_id.uos_id.id,
            'goods_qty': qty,
            'uom_id': line.uom_id.id,
            'cost_unit': line.price,
            'price_taxed': line.price_taxed,
            'discount_rate': line.discount_rate,
            'discount_amount': discount_amount,
            'tax_rate': line.tax_rate,
            'note': line.note or '',
        }

    def _generate_receipt(self, receipt_line):
        '''根据明细行生成入库单或退货单'''
        # 如果退货，warehouse_dest_id，warehouse_id要调换
        warehouse = (self.type == 'buy'
                     and self.env.ref("warehouse.warehouse_supplier")
                     or self.warehouse_dest_id)
        warehouse_dest = (self.type == 'buy'
                          and self.warehouse_dest_id
                          or self.env.ref("warehouse.warehouse_supplier"))
        rec = (self.type == 'buy' and self.with_context(is_return=False)
               or self.with_context(is_return=True))
        receipt_id = rec.env['buy.receipt'].create({
            'partner_id': self.partner_id.id,
            'warehouse_id': warehouse.id,
            'warehouse_dest_id': warehouse_dest.id,
            'date': self.planned_date,
            'date_due': self.planned_date,
            'order_id': self.id,
            'ref':self.ref,
            'origin': 'buy.receipt',
            'note': self.note,
            'discount_rate': self.discount_rate,
            'discount_amount': self.discount_amount,
            'invoice_by_receipt': self.invoice_by_receipt,
            'currency_id': self.currency_id.id,
        })
        if self.type == 'buy':
            receipt_id.write({'line_in_ids': [
                (0, 0, line[0]) for line in receipt_line]})
        else:
            receipt_id.write({'line_out_ids': [
                (0, 0, line[0]) for line in receipt_line]})
        return receipt_id

    @api.one
    def buy_generate_receipt(self):
        '''由购货订单生成采购入库/退货单'''
        receipt_line = []  # 采购入库/退货单行

        for line in self.line_ids:
            # 如果订单部分入库，则点击此按钮时生成剩余数量的入库单
            to_in = line.quantity - line.quantity_in
            if to_in <= 0:
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
        receipt_id = self._generate_receipt(receipt_line)
        view_id = (self.type == 'buy'
                   and self.env.ref('buy.buy_receipt_form').id
                   or self.env.ref('buy.buy_return_form').id)
        name = (self.type == 'buy' and u'采购入库单' or u'采购退货单')

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

    @api.multi
    def action_view_receipt(self):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        '''

        self.ensure_one()
        name = (self.type == 'buy' and u'采购入库单' or u'采购退货单')
        action = {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'buy.receipt',
            'view_id': False,
            'target': 'current',
        }

        #receipt_ids = sum([order.receipt_ids.ids for order in self], [])
        receipt_ids = self.receipt_ids.ids
        # choose the view_mode accordingly
        if len(receipt_ids) > 1:
            action['domain'] = "[('id','in',[" + \
                ','.join(map(str, receipt_ids)) + "])]"
            action['view_mode'] = 'tree,form'
        elif len(receipt_ids) == 1:
            view_id = (self.type == 'buy'
                       and self.env.ref('buy.buy_receipt_form').id
                       or self.env.ref('buy.buy_return_form').id)
            action['views'] = [(view_id, 'form')]
            action['res_id'] = receipt_ids and receipt_ids[0] or False
        return action

    @api.multi
    def action_view_invoice(self):
        '''
        This function returns an action that display existing invoices of given purchase order ids( linked/computed via buy.receipt).
        When only one found, show the invoice immediately.
        '''

        self.ensure_one()
        if self.invoice_count == 0:
            return False
        action = {
            'name': u'结算单（供应商发票）',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'money.invoice',
            'view_id': False,
            'target': 'current',
        }
        invoice_ids = self.invoice_ids.ids
        # choose the view_mode accordingly
        if len(invoice_ids) > 1:
            action['domain'] = "[('id','in',[" + \
                ','.join(map(str, invoice_ids)) + "])]"
            action['view_mode'] = 'tree'
        elif len(invoice_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = invoice_ids and invoice_ids[0] or False
        return action


class BuyOrderLine(models.Model):
    _name = 'buy.order.line'
    _description = u'购货订单明细'

    @api.one
    @api.depends('goods_id')
    def _compute_using_attribute(self):
        '''返回订单行中商品是否使用属性'''
        self.using_attribute = self.goods_id.attribute_ids and True or False

    @api.one
    @api.depends('quantity', 'price_taxed', 'discount_amount', 'tax_rate')
    def _compute_all_amount(self):
        '''当订单行的数量、含税单价、折扣额、税率改变时，改变购货金额、税额、价税合计'''
        if self.tax_rate > 100:
            raise UserError(u'税率不能输入超过100的数')
        if self.tax_rate < 0:
            raise UserError(u'税率不能输入负数')
        if self.order_id.currency_id.id == self.env.user.company_id.currency_id.id:
            # 单据上外币是公司本位币
            self.price = self.price_taxed / (1 + self.tax_rate * 0.01)  # 不含税单价
            self.subtotal = self.price_taxed * self.quantity - self.discount_amount  # 价税合计
            self.tax_amount = self.subtotal / \
                (100 + self.tax_rate) * self.tax_rate  # 税额
            self.amount = self.subtotal - self.tax_amount  # 金额
        else:
            # 非公司本位币
            rate_silent = (self.env['res.currency'].get_rate_silent(
                self.order_id.date,
                self.order_id.currency_id.id) or 1)
            currency_amount = self.quantity * self.price_taxed - self.discount_amount
            self.price = self.price_taxed * \
                rate_silent / (1 + self.tax_rate * 0.01)
            self.subtotal = (self.price_taxed * self.quantity -
                             self.discount_amount) * rate_silent  # 价税合计
            self.tax_amount = self.subtotal / \
                (100 + self.tax_rate) * self.tax_rate  # 税额
            self.amount = self.subtotal - self.tax_amount  # 本位币金额
            self.currency_amount = currency_amount  # 外币金额

    @api.one
    def _inverse_price(self):
        '''由不含税价反算含税价，保存时生效'''
        self.price_taxed = self.price * (1 + self.tax_rate * 0.01)

    @api.onchange('price', 'tax_rate')
    def onchange_price(self):
        '''当订单行的不含税单价改变时，改变含税单价'''
        price = self.price_taxed / (1 + self.tax_rate * 0.01)  # 不含税单价
        decimal = self.env.ref('core.decimal_price')
        if float_compare(price, self.price, precision_digits=decimal.digits) != 0:
            self.price_taxed = self.price * (1 + self.tax_rate * 0.01)

    order_id = fields.Many2one('buy.order',
                               u'订单编号',
                               index=True,
                               required=True,
                               ondelete='cascade',
                               help=u'关联订单的编号')
    goods_id = fields.Many2one('goods',
                               u'商品',
                               ondelete='restrict',
                               help=u'商品')
    using_attribute = fields.Boolean(u'使用属性',
                                     compute=_compute_using_attribute,
                                     help=u'商品是否使用属性')
    attribute_id = fields.Many2one('attribute',
                                   u'属性',
                                   ondelete='restrict',
                                   domain="[('goods_id', '=', goods_id)]",
                                   help=u'商品的属性，当商品有属性时，该字段必输')
    uom_id = fields.Many2one('uom',
                             u'单位',
                             ondelete='restrict',
                             help=u'商品计量单位')
    quantity = fields.Float(u'数量',
                            default=1,
                            required=True,
                            digits=dp.get_precision('Quantity'),
                            help=u'下单数量')
    quantity_in = fields.Float(u'已执行数量',
                               copy=False,
                               digits=dp.get_precision('Quantity'),
                               help=u'购货订单产生的入库单/退货单已执行数量')
    price = fields.Float(u'购货单价',
                         compute=_compute_all_amount,
                         inverse=_inverse_price,
                         store=True,
                         digits=dp.get_precision('Price'),
                         help=u'不含税单价，由含税单价计算得出')
    price_taxed = fields.Float(u'含税单价',
                               digits=dp.get_precision('Price'),
                               help=u'含税单价，取自商品成本或对应供应商的购货价')
    discount_rate = fields.Float(u'折扣率%',
                                 help=u'折扣率')
    discount_amount = fields.Float(u'折扣额',
                                   digits=dp.get_precision('Amount'),
                                   help=u'输入折扣率后自动计算得出，也可手动输入折扣额')
    amount = fields.Float(u'金额',
                          compute=_compute_all_amount,
                          store=True,
                          digits=dp.get_precision('Amount'),
                          help=u'金额  = 价税合计  - 税额')
    currency_amount = fields.Float(u'外币金额',
                                   compute=_compute_all_amount,
                                   store=True,
                                   digits=dp.get_precision('Amount'),
                                   help=u'外币金额')
    tax_rate = fields.Float(u'税率(%)',
                            default=lambda self: self.env.user.company_id.import_tax_rate,
                            help=u'默认值取公司进项税率')
    tax_amount = fields.Float(u'税额',
                              compute=_compute_all_amount,
                              store=True,
                              digits=dp.get_precision('Amount'),
                              help=u'由税率计算得出')
    subtotal = fields.Float(u'价税合计',
                            compute=_compute_all_amount,
                            store=True,
                            digits=dp.get_precision('Amount'),
                            help=u'含税单价 乘以 数量')
    note = fields.Char(u'备注',
                       help=u'本行备注')
    # TODO:放到单独模块中 sell_to_buy many2one 到sell.order
    origin = fields.Char(u'销售单号',
                         help=u'以销订购的销售订单号')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.onchange('goods_id', 'quantity')
    def onchange_goods_id(self):
        '''当订单行的商品变化时，带出商品上的单位、成本价。
        在采购订单上选择供应商，自动带出供货价格，没有设置供货价的取成本价格。'''
        if not self.order_id.partner_id:
            raise UserError(u'请先选择一个供应商！')
        if self.goods_id:
            self.uom_id = self.goods_id.uom_id
            self.price_taxed = self.goods_id.cost
            for line in self.goods_id.vendor_ids:
                if line.vendor_id == self.order_id.partner_id \
                        and self.quantity >= line.min_qty:
                    self.price_taxed = line.price
                    break

            if self.goods_id.tax_rate and self.order_id.partner_id.tax_rate:
                if self.goods_id.tax_rate >= self.order_id.partner_id.tax_rate:
                    self.tax_rate = self.order_id.partner_id.tax_rate
                else:
                    self.tax_rate = self.goods_id.tax_rate
            elif self.goods_id.tax_rate and not self.order_id.partner_id.tax_rate:
                self.tax_rate = self.goods_id.tax_rate
            elif not self.goods_id.tax_rate and self.order_id.partner_id.tax_rate:
                self.tax_rate = self.order_id.partner_id.tax_rate
            else:
                self.tax_rate = self.env.user.company_id.import_tax_rate

    @api.onchange('quantity', 'price_taxed', 'discount_rate')
    def onchange_discount_rate(self):
        '''当数量、单价或优惠率发生变化时，优惠金额发生变化'''
        price = self.price_taxed / (1 + self.tax_rate * 0.01)
        self.discount_amount = (self.quantity * price *
                                self.discount_rate * 0.01)


class Payment(models.Model):
    _name = "payment.plan"
    _description = u'付款计划'

    name = fields.Char(string=u"名称", required=True,
                       help=u'付款计划名称')
    amount_money = fields.Float(string=u"金额", required=True,
                                help=u'付款金额')
    date_application = fields.Date(string=u"申请日期", readonly=True,
                                   help=u'付款申请日期')
    buy_id = fields.Many2one("buy.order",
                             help=u'关联的购货订单')

    @api.one
    def request_payment(self):
        categ = self.env.ref('money.core_category_purchase')
        if not float_is_zero(self.amount_money, 2):
            source_id = self.env['money.invoice'].create({
                'name': self.buy_id.name,
                'partner_id': self.buy_id.partner_id.id,
                'category_id': categ.id,
                'date': fields.Date.context_today(self),
                'amount': self.amount_money,
                'reconciled': 0,
                'to_reconcile': self.amount_money,
                'date_due': fields.Date.context_today(self),
                'state': 'draft',
            })
            self.with_context(type='pay').env["money.order"].create({
                'partner_id': self.buy_id.partner_id.id,
                'bank_name': self.buy_id.partner_id.bank_name,
                'bank_num': self.buy_id.partner_id.bank_num,
                'date': fields.Date.context_today(self),
                'source_ids':
                [(0, 0, {'name': source_id.id,
                         'category_id': categ.id,
                         'date': source_id.date,
                         'amount': self.amount_money,
                         'reconciled': 0.0,
                         'to_reconcile': self.amount_money,
                         'this_reconcile': self.amount_money})],
                'type': 'pay',
                'amount': self.amount_money,
                'reconciled': 0,
                'to_reconcile': self.amount_money,
                'state': 'draft',
            })
        self.date_application = datetime.now()
