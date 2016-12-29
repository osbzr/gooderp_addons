# -*- coding: utf-8 -*-

from odoo import fields, models, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_compare

# 销货订单审核状态可选值
SELL_ORDER_STATES = [
    ('draft', u'未审核'),
    ('done', u'已审核'),
]

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
}


class sell_order(models.Model):
    _name = 'sell.order'
    _description = u'销货订单'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    @api.one
    @api.depends('line_ids.subtotal', 'discount_amount')
    def _compute_amount(self):
        '''当订单行和优惠金额改变时，改变优惠后金额'''
        total = sum(line.subtotal for line in self.line_ids)
        self.amount = total - self.discount_amount

    @api.one
    @api.depends('line_ids.quantity', 'line_ids.quantity_out')
    def _get_sell_goods_state(self):
        '''返回发货状态'''
        if all(line.quantity_out == 0 for line in self.line_ids):
            self.goods_state = u'未出库'
        elif any(line.quantity > line.quantity_out for line in self.line_ids):
            self.goods_state = u'部分出库'
        else:
            self.goods_state = u'全部出库'

    @api.one
    @api.depends('partner_id')
    def _compute_currency_id(self):
        self.currency_id = self.partner_id.c_category_id.account_id.currency_id.id or self.partner_id.s_category_id.account_id.currency_id.id
        if not self.currency_id :
            self.currency_id = self.env.user.company_id.currency_id.id

    @api.model
    def _default_warehouse(self):
        return self._default_warehouse_impl()
    @api.model
    def _default_warehouse_impl(self):
        if self.env.context.get('warehouse_type'):
            return self.env['warehouse'].get_warehouse_by_type(
                        self.env.context.get('warehouse_type'))

        return self.env['warehouse'].browse()

    @api.one
    @api.depends('type')
    def _get_money_state(self):
        '''计算销货订单收款/退款状态'''
        deliverys = self.env['sell.delivery'].search([('order_id', '=', self.id)])
        if all(delivery.invoice_id.reconciled == 0
               for delivery in deliverys):
            self.money_state = (self.type == 'sell' and u'未收款' or u'未退款')
        elif all(delivery.invoice_id.reconciled ==
                 delivery.invoice_id.amount for delivery in deliverys):
            self.money_state = (self.type == 'sell' and u'全部收款' or u'全部退款')
        else:
            self.money_state = (self.type == 'sell' and u'部分收款' or u'部分退款')

    partner_id = fields.Many2one('partner', u'客户',
                            ondelete='restrict', states=READONLY_STATES,
                                 help=u'签约合同的客户')
    contact = fields.Char(u'联系人', states=READONLY_STATES,
                                 help=u'客户方的联系人')
    address = fields.Char(u'地址', states=READONLY_STATES,
                                 help=u'联系地址')
    mobile = fields.Char(u'手机', states=READONLY_STATES,
                                 help=u'联系手机')
    staff_id = fields.Many2one('staff', u'销售员',
                            ondelete='restrict', states=READONLY_STATES,
                            default=lambda self: self.env.user.employee_ids and self.env.user.employee_ids[0],
                                 help=u'单据负责人')
    date = fields.Date(u'单据日期', states=READONLY_STATES,
                       default=lambda self: fields.Date.context_today(self),
                       index=True, copy=False, help=u"默认是订单创建日期")
    delivery_date = fields.Date(
        u'要求交货日期', states=READONLY_STATES,
        default=lambda self: fields.Date.context_today(self),
        index=True, copy=False, help=u"订单的要求交货日期")
    type = fields.Selection([('sell', u'销货'), ('return', u'退货')], u'类型', 
                            default='sell', states=READONLY_STATES,
                            help=u'销货订单的类型，分为销货或退货')
    warehouse_id = fields.Many2one('warehouse', u'调出仓库',
                                   ondelete='restrict', states=READONLY_STATES,
                                   default=_default_warehouse,
                                   help=u'产品将从该仓库调出')
    name = fields.Char(u'单据编号', index=True, copy=False,
                       default='/', help=u"创建时它会自动生成下一个编号")
    line_ids = fields.One2many('sell.order.line', 'order_id', u'销货订单行',
                               states=READONLY_STATES, copy=True,
                               help=u'销货订单的明细行，不能为空')
    note = fields.Text(u'备注', help=u'单据备注')
    discount_rate = fields.Float(u'优惠率(%)', states=READONLY_STATES,
                                 help=u'整单优惠率')
    discount_amount = fields.Float(u'优惠金额', states=READONLY_STATES, 
                                   track_visibility='always',
                                   digits=dp.get_precision('Amount'),
                                   help=u'整单优惠金额，可由优惠率自动计算出来，也可手动输入')
    amount = fields.Float(string=u'优惠后金额', store=True, readonly=True,
                        compute='_compute_amount', track_visibility='always',
                        digits=dp.get_precision('Amount'),
                        help=u'总金额减去优惠金额')
    pre_receipt = fields.Float(u'预收款', states=READONLY_STATES,
                           digits=dp.get_precision('Amount'),
                           help=u'输入预收款审核销货订单，会产生一张收款单')
    bank_account_id = fields.Many2one('bank.account', u'结算账户',
                                      ondelete='restrict',
                                      help=u'用来核算和监督企业与其他单位或个人之间的债权债务的结算情况')
    approve_uid = fields.Many2one('res.users', u'审核人', copy=False,
                                  ondelete='restrict',
                                  help=u'审核单据的人')
    state = fields.Selection(SELL_ORDER_STATES, u'审核状态', readonly=True,
                             help=u"销货订单的审核状态", index=True,
                             copy=False, default='draft')
    goods_state = fields.Char(u'发货状态', compute=_get_sell_goods_state,
                              default=u'未出库',
                              store=True,
                              help=u"销货订单的发货状态", index=True, copy=False)
    money_state = fields.Char(u'收/退款状态',
                              compute=_get_money_state,
                              copy=False,
                              help=u'销货订单生成的发货单或退货单的收/退款状态')
    cancelled = fields.Boolean(u'已终止',
                               help=u'该单据是否已终止')
    currency_id = fields.Many2one('res.currency',
                                  u'外币币别',
                                  compute='_compute_currency_id',
                                  store=True,
                                  readonly=True,
                                  help=u'外币币别')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''选择客户带出其默认地址信息'''
        if self.partner_id:
            self.contact = self.partner_id.contact
            self.address = self.partner_id.address
            self.mobile = self.partner_id.mobile

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
                    line.tax_rate = self.env.user.company_id.output_tax_rate

    @api.onchange('discount_rate', 'line_ids')
    def onchange_discount_rate(self):
        '''当优惠率或销货订单行发生变化时，单据优惠金额发生变化'''
        total = sum(line.subtotal for line in self.line_ids)
        self.discount_amount = total * self.discount_rate * 0.01

    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise UserError(u'不能删除已审核的销货订单')

        return super(sell_order, self).unlink()

    def _get_vals(self):
        '''返回创建 money_order 时所需数据'''
        flag = (self.type == 'sell' and 1 or -1) # 用来标志发库或退货
        amount = flag * self.amount
        this_reconcile = flag * self.pre_receipt
        money_lines = [{
            'bank_id': self.bank_account_id.id,
            'amount': this_reconcile,
        }]
        return {
            'partner_id': self.partner_id.id,
            'date': fields.Date.context_today(self),
            'line_ids':
            [(0, 0, line) for line in money_lines],
            'amount': amount,
            'reconciled': this_reconcile,
            'to_reconcile': amount,
            'state': 'draft',
            'origin_name': self.name,
        }

    @api.one
    def generate_receipt_order(self):
        '''由销货订单生成收款单'''
        # 发库单/退货单
        if self.pre_receipt:
            money_order = self.with_context(type='get').env['money.order'].create(
                self._get_vals()
            )
            money_order.money_order_done()

    @api.one
    def sell_order_done(self):
        '''审核销货订单'''
        if self.state == 'done':
            raise UserError(u'请不要重复审核！')
        if not self.line_ids:
            raise UserError(u'请输入产品明细行！')
        for line in self.line_ids:
            if line.quantity <= 0 or line.price_taxed < 0:
                raise UserError(u'产品 %s 的数量和含税单价不能小于0！' % line.goods_id.name)
            if line.tax_amount > 0 and self.currency_id != self.env.user.company_id.currency_id:
                raise UserError(u'外贸免税！')
        if not self.bank_account_id and self.pre_receipt:
            raise UserError(u'预付款不为空时，请选择结算账户！')
        # 销售预收款生成收款单
        self.generate_receipt_order()
        self.sell_generate_delivery()
        self.state = 'done'
        self.approve_uid = self._uid

    @api.one
    def sell_order_draft(self):
        '''反审核销货订单'''
        if self.state == 'draft':
            raise UserError(u'请不要重复反审核！')
        if self.goods_state != u'未出库':
            raise UserError(u'该销货订单已经发货，不能反审核！')
        # 查找产生的发货单并删除
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.name)])
        delivery.unlink()
        # 查找产生的收款单并删除
        money_order = self.env['money.order'].search(
                          [('origin_name','=',self.name)])
        if money_order:
            money_order.money_order_draft()
            money_order.unlink()
        self.state = 'draft'
        self.approve_uid = ''

    @api.one
    def get_delivery_line(self, line, single=False):
        '''返回销售发货/退货单行'''
        qty = 0
        discount_amount = 0
        if single:
            qty = 1
            discount_amount = line.discount_amount \
                    / ((line.quantity - line.quantity_out) or 1)
        else:
            qty = line.quantity - line.quantity_out
            discount_amount = line.discount_amount

        return {
            'sell_line_id': line.id,
            'goods_id': line.goods_id.id,
            'attribute_id': line.attribute_id.id,
            'goods_uos_qty': line.goods_id.conversion and qty / line.goods_id.conversion or 0,
            'uos_id': line.goods_id.uos_id.id,
            'goods_qty': qty,
            'uom_id': line.uom_id.id,
            'price_taxed': line.price_taxed,
            'discount_rate': line.discount_rate,
            'discount_amount': discount_amount,
            'tax_rate': line.tax_rate,
            'note': line.note or '',
        }

    def _generate_delivery(self, delivery_line):
        '''根据明细行生成发货单或退货单'''
        # 如果退货，warehouse_dest_id，warehouse_id要调换
        warehouse = (self.type == 'sell'
                     and self.warehouse_id
                     or self.env.ref("warehouse.warehouse_customer"))
        warehouse_dest = (self.type == 'sell'
                          and self.env.ref("warehouse.warehouse_customer")
                          or self.warehouse_id)
        rec = (self.type == 'sell' and self.with_context(is_return=False)
               or self.with_context(is_return=True))
        delivery_id = rec.env['sell.delivery'].create({
            'partner_id': self.partner_id.id,
            'warehouse_id': warehouse.id,
            'warehouse_dest_id': warehouse_dest.id,
            'staff_id': self.staff_id.id,
            'date': self.delivery_date,
            'order_id': self.id,
            'origin': 'sell.delivery',
            'note': self.note,
            'discount_rate': self.discount_rate,
            'discount_amount': self.discount_amount,
            'currency_id': self.currency_id.id,
            'contact': self.contact,
            'address': self.address,
            'mobile': self.mobile
        })
        if self.type == 'sell':
            delivery_id.write({'line_out_ids': [
                (0, 0, line[0]) for line in delivery_line]})
        else:
            delivery_id.write({'line_in_ids': [
                (0, 0, line[0]) for line in delivery_line]})
        return delivery_id

    @api.one
    def sell_generate_delivery(self):
        '''由销货订单生成销售发货单'''
        delivery_line = []  # 销售发货单行

        for line in self.line_ids:
            # 如果订单部分出库，则点击此按钮时生成剩余数量的出库单
            to_out = line.quantity - line.quantity_out
            if to_out <= 0:
                continue
            if line.goods_id.force_batch_one:
                i = 0
                while i < to_out:
                    i += 1
                    delivery_line.append(
                        self.get_delivery_line(line, single=True))
            else:
                delivery_line.append(
                    self.get_delivery_line(line, single=False))

        if not delivery_line:
            return {}
        delivery_id = self._generate_delivery(delivery_line)
        view_id = (self.type == 'sell'
                   and self.env.ref('sell.sell_delivery_form').id
                   or self.env.ref('sell.sell_return_form').id)
        name = (self.type == 'sell' and u'销售发货单' or u'销售退货单')
        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view_id, 'form')],
            'res_model': 'sell.delivery',
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', delivery_id)],
            'target': 'current',
        }


class sell_order_line(models.Model):
    _name = 'sell.order.line'
    _description = u'销货订单明细'

    @api.one
    @api.depends('goods_id')
    def _compute_using_attribute(self):
        '''返回订单行中产品是否使用属性'''
        self.using_attribute = self.goods_id.attribute_ids and True or False

    @api.one
    @api.depends('quantity', 'price_taxed', 'discount_amount', 'tax_rate')
    def _compute_all_amount(self):
        '''当订单行的数量、含税单价、折扣额、税率改变时，改变销售金额、税额、价税合计'''
        if self.tax_rate > 100:
            raise UserError('税率不能输入超过100的数!\n输入税率:%s'%self.tax_rate)
        if self.tax_rate < 0:
            raise UserError('税率不能输入负数\n 输入税率:%s'%self.tax_rate)
        if self.order_id.currency_id.id == self.env.user.company_id.currency_id.id:
            self.price = self.price_taxed / (1 + self.tax_rate * 0.01) # 不含税单价
            self.subtotal = self.price_taxed * self.quantity - self.discount_amount # 价税合计
            self.tax_amount = self.subtotal / (100 + self.tax_rate) * self.tax_rate # 税额
            self.amount = self.subtotal - self.tax_amount # 金额
        else:
            rate_silent = self.order_id.currency_id.rate or self.env.user.company_id.currency_id.rate
            currency_amount = self.quantity * self.price_taxed - self.discount_amount
            self.price = self.price_taxed * rate_silent / (1 + self.tax_rate * 0.01)
            self.subtotal = (self.price_taxed * self.quantity - self.discount_amount) * rate_silent  # 价税合计
            self.tax_amount = self.subtotal / (100 + self.tax_rate) * self.tax_rate # 税额
            self.amount = self.subtotal - self.tax_amount # 本位币金额
            self.currency_amount = currency_amount  # 外币金额

    order_id = fields.Many2one('sell.order', u'订单编号', index=True,
                               required=True, ondelete='cascade',
                               help=u'关联订单的编号')
    currency_amount = fields.Float(u'外币金额', compute=_compute_all_amount,
                          store=True, readonly=True,
                          digits=dp.get_precision(u'金额'),
                          help=u'外币金额')
    goods_id = fields.Many2one('goods', u'商品', ondelete='restrict',
                               help=u'商品')
    using_attribute = fields.Boolean(u'使用属性', compute=_compute_using_attribute,
                               help=u'商品是否使用属性')
    attribute_id = fields.Many2one('attribute', u'属性',
                                   ondelete='restrict', 
                                   domain="[('goods_id', '=', goods_id)]",
                                   help=u'商品的属性，当商品有属性时，该字段必输')
    uom_id = fields.Many2one('uom', u'单位', ondelete='restrict',
                             help=u'商品计量单位')
    quantity = fields.Float(u'数量', default=1,
                            digits=dp.get_precision('Quantity'),
                            help=u'下单数量')
    quantity_out = fields.Float(u'已执行数量', copy=False,
                                digits=dp.get_precision('Quantity'),
                                help=u'销货订单产生的发货单/退货单已执行数量')
    price = fields.Float(u'销售单价', compute=_compute_all_amount,
                         store=True, readonly=True,
                         digits=(12, 6),
                         help=u'不含税单价，由含税单价计算得出')
    price_taxed = fields.Float(u'含税单价',digits=(12, 6),
                         help=u'含税单价，取商品零售价')
    discount_rate = fields.Float(u'折扣率%',
                                   help=u'折扣率')
    discount_amount = fields.Float(u'折扣额',
                                   help=u'输入折扣率后自动计算得出，也可手动输入折扣额')
    amount = fields.Float(u'金额', compute=_compute_all_amount, 
                          store=True, readonly=True,
                          digits=dp.get_precision('Amount'),
                          help=u'金额  = 价税合计  - 税额')
    tax_rate = fields.Float(u'税率(%)',
                            help=u'税率')
    tax_amount = fields.Float(u'税额', compute=_compute_all_amount, store=True, 
                              readonly=True,
                              digits=dp.get_precision('Amount'),
                              help=u'税额')
    subtotal = fields.Float(u'价税合计', compute=_compute_all_amount, 
                            store=True, readonly=True,
                            digits=dp.get_precision('Amount'),
                            help=u'含税单价 乘以 数量')
    note = fields.Char(u'备注',
                       help=u'本行备注')

    @api.onchange('goods_id')
    def onchange_warehouse_id(self):
        '''当订单行的仓库变化时，带出定价策略中的折扣率'''
        if self.order_id.warehouse_id and self.goods_id:
            partner = self.order_id.partner_id
            warehouse = self.order_id.warehouse_id
            goods = self.goods_id
            date = self.order_id.date
            pricing = self.env['pricing'].get_pricing_id(partner,warehouse,goods,date)
            if pricing:
                self.discount_rate = pricing.discount_rate
            else:
                self.discount_rate = 0

    @api.onchange('goods_id')
    def onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的单位、默认仓库、价格、税率'''
        if self.goods_id:
            self.uom_id = self.goods_id.uom_id
            self.price_taxed = self.goods_id.price
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
                self.tax_rate = self.env.user.company_id.output_tax_rate

    @api.onchange('quantity', 'price_taxed', 'discount_rate')
    def onchange_discount_rate(self):
        '''当数量、单价或优惠率发生变化时，优惠金额发生变化'''
        price = (self.tax_rate != -100
                 and self.price_taxed / (1 + self.tax_rate * 0.01) or 0)
        self.discount_amount = self.quantity * price \
                * self.discount_rate * 0.01
