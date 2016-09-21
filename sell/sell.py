# -*- encoding: utf-8 -*-

from openerp import fields, models, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm

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
        '''返回收货状态'''
        for line in self.line_ids:
            if line.quantity_out == 0:
                self.goods_state = u'未出库'
            elif line.quantity > line.quantity_out:
                self.goods_state = u'部分出库'
                break
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
        if self.env.context.get('warehouse_type'):
            return self.env['warehouse'].get_warehouse_by_type(
                        self.env.context.get('warehouse_type'))

        return self.env['warehouse'].browse()

    @api.one
    @api.depends('amount', 'amount_executed')
    def _get_money_state(self):
        '''计算销货订单收款/退款状态'''
        if self.amount_executed == 0:
            self.money_state = (self.type == 'sell') and u'未收款' or u'未退款'
        elif self.amount_executed < self.amount:
            self.money_state = (self.type == 'sell') and u'部分收款' or u'部分退款'
        elif self.amount_executed == self.amount:
            self.money_state = (self.type == 'sell') and u'全部收款' or u'全部退款'

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
                                 help=u'单据负责人')
    date = fields.Date(u'单据日期', states=READONLY_STATES,
                       default=lambda self: fields.Date.context_today(self),
                       select=True, copy=False, help=u"默认是订单创建日期")
    delivery_date = fields.Date(
        u'要求交货日期', states=READONLY_STATES,
        default=lambda self: fields.Date.context_today(self),
        select=True, copy=False, help=u"订单的要求交货日期")
    type = fields.Selection([('sell', u'销货'), ('return', u'退货')], u'类型', 
                            default='sell', states=READONLY_STATES,
                            help=u'销货订单的类型，分为销货或退货')
    warehouse_id = fields.Many2one('warehouse', u'调出仓库',
                                   ondelete='restrict', states=READONLY_STATES,
                                   default=_default_warehouse,
                                   help=u'产品将从该仓库调出')
    name = fields.Char(u'单据编号', select=True, copy=False,
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
                             help=u"销货订单的审核状态", select=True, 
                             copy=False, default='draft')
    goods_state = fields.Char(u'发货状态', compute=_get_sell_goods_state,
                              default=u'未出库',
                              store=True,
                              help=u"销货订单的发货状态", select=True, copy=False)
    amount_executed = fields.Float(u'已执行金额',
                                   help=u'发货单已收款金额或退货单已退款金额')
    money_state = fields.Char(u'收/退款状态',
                              compute=_get_money_state,
                              store=True,
                              help=u'销货订单生成的发货单或退货单的收/退款状态')
    cancelled = fields.Boolean(u'已终止',
                               help=u'该单据是否已终止')
    currency_id = fields.Many2one('res.currency',
                                  u'外币币别',
                                  compute='_compute_currency_id',
                                  store=True,
                                  readonly=True,
                                  help=u'外币币别')

    @api.one
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''选择客户带出其默认地址信息'''
        if self.partner_id:
            self.contact = self.partner_id.contact
            self.address = self.partner_id.address
            self.mobile = self.partner_id.mobile

    @api.one
    @api.onchange('discount_rate', 'line_ids')
    def onchange_discount_rate(self):
        '''当优惠率或销货订单行发生变化时，单据优惠金额发生变化'''
        total = sum(line.subtotal for line in self.line_ids)
        self.discount_amount = total * self.discount_rate * 0.01

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get(self._name) or '/'

        return super(sell_order, self).create(vals)

    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise except_orm(u'错误', u'不能删除已审核的单据')

        return super(sell_order, self).unlink()

    @api.one
    def generate_receipt_order(self):
        '''由销货订单生成收款单'''
        # 入库单/退货单
        if self.type == 'sell':
            amount = self.amount
            this_reconcile = self.pre_receipt
        else:
            amount = - self.amount
            this_reconcile = - self.pre_receipt
        if self.pre_receipt:
            money_lines = []
            money_lines.append({
                'bank_id': self.bank_account_id.id,
                'amount': this_reconcile,
            })

            rec = self.with_context(type='get')
            money_order = rec.env['money.order'].create({
                                'partner_id': self.partner_id.id,
                                'date': fields.Date.context_today(self),
                                'line_ids':
                                [(0, 0, line) for line in money_lines],
                                'type': 'get',
                                'amount': amount,
                                'reconciled': this_reconcile,
                                'to_reconcile': amount,
                                'state': 'draft',
                                'origin_name':self.name,
                            })
            money_order.money_order_done()

    @api.one
    def sell_order_done(self):
        '''审核销货订单'''
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        if not self.line_ids:
            raise except_orm(u'错误', u'请输入产品明细行！')
        for line in self.line_ids:
            if line.quantity <= 0 or line.price_taxed < 0:
                raise except_orm(u'错误', u'产品 %s 的数量和含税单价不能小于0！' % line.goods_id.name)
        if self.bank_account_id and not self.pre_receipt:
            raise except_orm(u'警告！', u'结算账户不为空时，需要输入预付款！')
        if not self.bank_account_id and self.pre_receipt:
            raise except_orm(u'警告！', u'预付款不为空时，请选择结算账户！')
        # 销售预收款生成收款单
        self.generate_receipt_order()
        self.sell_generate_delivery()
        self.state = 'done'
        self.approve_uid = self._uid

    @api.one
    def sell_order_draft(self):
        '''反审核销货订单'''
        if self.state == 'draft':
            raise except_orm(u'错误', u'请不要重复反审核！')
        if self.goods_state != u'未出库':
            raise except_orm(u'错误', u'该销货订单已经发货，不能反审核！')
        else:
            # 查找产生的发货单并删除
            delivery = self.env['sell.delivery'].search(
                [('order_id', '=', self.name)])
            if delivery:
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
                    / (line.quantity - line.quantity_out)
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

    @api.one
    def sell_generate_delivery(self):
        '''由销货订单生成销售发货单'''
        # 如果退货，warehouse_dest_id，warehouse_id要调换
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
        if self.type == 'sell':
            delivery_id = self.env['sell.delivery'].create({
                'partner_id': self.partner_id.id,
                'warehouse_id': self.warehouse_id.id,
                'warehouse_dest_id': self.env.ref("warehouse.warehouse_customer").id,
                'staff_id': self.staff_id.id,
                'date': self.delivery_date,
                'order_id': self.id,
                'origin': 'sell.delivery',
                'line_out_ids': [(0, 0, line[0]) for line in delivery_line],
                'note': self.note,
                'discount_rate': self.discount_rate,
                'discount_amount': self.discount_amount,
                'currency_id': self.currency_id.id
            })
            view_id = self.env['ir.model.data']\
                    .xmlid_to_res_id('sell.sell_delivery_form')
            name = u'销售发货单'
        elif self.type == 'return':
            rec = self.with_context(is_return=True)
            delivery_id = rec.env['sell.delivery'].create({
                'partner_id': self.partner_id.id,
                'warehouse_id': self.env.ref("warehouse.warehouse_customer").id,
                'warehouse_dest_id': self.warehouse_id.id,
                'staff_id': self.staff_id.id,
                'date': self.delivery_date,
                'order_id': self.id,
                'origin': 'sell.delivery',
                'line_in_ids': [(0, 0, line[0]) for line in delivery_line],
                'note': self.note,
                'discount_rate': self.discount_rate,
                'discount_amount': self.discount_amount,
                'currency_id': self.currency_id.id
            })
            view_id = self.env['ir.model.data']\
                    .xmlid_to_res_id('sell.sell_return_form')
            name = u'销售退货单'
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
        if self.order_id.currency_id.id == self.env.user.company_id.currency_id.id :
            self.price = self.price_taxed / (1 + self.tax_rate * 0.01)
            self.amount = self.quantity * self.price - self.discount_amount  # 折扣后金额
            self.tax_amount = self.amount * self.tax_rate * 0.01  # 税额
            self.subtotal = self.amount + self.tax_amount
        else :
            rate_silent = self.order_id.currency_id.rate_silent or self.env.user.company_id.currency_id.rate_silent
            currency_amount = self.quantity * self.price_taxed - self.discount_amount
            self.price = self.price_taxed * rate_silent / (1 + self.tax_rate * 0.01)
            self.amount = currency_amount * rate_silent
            self.tax_amount = self.amount * self.tax_rate * 0.01
            self.subtotal = self.amount + self.tax_amount
            self.currency_amount = currency_amount

    order_id = fields.Many2one('sell.order', u'订单编号', select=True, 
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
                            default=lambda self:self.env.user.company_id.output_tax_rate,
                            help=u'默认值取公司销项税率')
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

    @api.one
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

    @api.one
    @api.onchange('goods_id')
    def onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的单位、默认仓库、价格'''
        if self.goods_id:
            self.uom_id = self.goods_id.uom_id
            self.price_taxed = self.goods_id.price

    @api.one
    @api.onchange('quantity', 'price_taxed', 'discount_rate')
    def onchange_discount_rate(self):
        '''当数量、单价或优惠率发生变化时，优惠金额发生变化'''
        price = self.price_taxed / (1 + self.tax_rate * 0.01)
        self.discount_amount = self.quantity * price \
                * self.discount_rate * 0.01

class sell_delivery(models.Model):
    _name = 'sell.delivery'
    _inherits = {'wh.move': 'sell_move_id'}
    _inherit = ['mail.thread']
    _description = u'销售发货单'
    _order = 'date desc, id desc'

    @api.one
    @api.depends('line_out_ids.subtotal', 'discount_amount', 'partner_cost', 
                 'receipt', 'partner_id', 'line_in_ids.subtotal')
    def _compute_all_amount(self):
        '''当优惠金额改变时，改变优惠后金额、本次欠款和总欠款'''
        total = 0
        if self.line_out_ids:
            # 发货时优惠前总金
            total = sum(line.subtotal for line in self.line_out_ids)
        elif self.line_in_ids:
            # 退货时优惠前总金额
            total = sum(line.subtotal for line in self.line_in_ids)
        self.amount = total - self.discount_amount
        self.debt = self.amount - self.receipt + self.partner_cost
        # 本次欠款变化时，总欠款应该变化
        self.total_debt = self.partner_id.receivable + self.debt

    @api.one
    @api.depends('is_return', 'invoice_id.reconciled', 'invoice_id.amount')
    def _get_sell_money_state(self):
        '''返回收款状态'''
        if not self.is_return:
            if self.invoice_id.reconciled == 0:
                self.money_state = u'未收款'
            elif self.invoice_id.reconciled < self.invoice_id.amount:
                self.money_state = u'部分收款'
            elif self.invoice_id.reconciled == self.invoice_id.amount:
                self.money_state = u'全部收款'

    @api.one
    @api.depends('is_return', 'invoice_id.reconciled', 'invoice_id.amount')
    def _get_sell_return_state(self):
        '''返回退款状态'''
        if self.is_return:
            if self.invoice_id.reconciled == 0:
                self.return_state = u'未退款'
            elif abs(self.invoice_id.reconciled) < abs(self.invoice_id.amount):
                self.return_state = u'部分退款'
            elif self.invoice_id.reconciled == self.invoice_id.amount:
                self.return_state = u'全部退款'

    currency_id = fields.Many2one('res.currency', u'外币币别', readonly=True,
                                  help=u'外币币别')
    sell_move_id = fields.Many2one('wh.move', u'发货单', required=True, 
                                   ondelete='cascade',
                                   help=u'发货单号')
    is_return = fields.Boolean(u'是否退货', default=lambda self: \
                               self.env.context.get('is_return'),
                               help=u'是否为退货类型')
    staff_id = fields.Many2one('staff', u'销售员', ondelete='restrict',
                               help=u'单据负责人')
    order_id = fields.Many2one('sell.order', u'源单号', copy=False,
                               ondelete='cascade',
                               help=u'产生发货单/退货单的销货订单')
    invoice_id = fields.Many2one('money.invoice', u'发票号',
                                 copy=False, ondelete='set null',
                                 help=u'产生的发票号')
    date_due = fields.Date(u'到期日期', copy=False,
                           default=lambda self: fields.Date.context_today(self),
                           help=u'收款截止日期')
    discount_rate = fields.Float(u'优惠率(%)', states=READONLY_STATES,
                                 help=u'整单优惠率')
    discount_amount = fields.Float(u'优惠金额', states=READONLY_STATES,
                            digits=dp.get_precision('Amount'),
                            help=u'整单优惠金额，可由优惠率自动计算得出，也可手动输入')
    amount = fields.Float(u'优惠后金额', compute=_compute_all_amount, 
                          store=True, readonly=True,
                          digits=dp.get_precision('Amount'),
                          help=u'总金额减去优惠金额')
    partner_cost = fields.Float(u'客户承担费用',
                        digits=dp.get_precision('Amount'),
                        help=u'客户承担费用')
    receipt = fields.Float(u'本次收款', states=READONLY_STATES,
                           digits=dp.get_precision('Amount'),
                           help=u'本次收款金额')
    bank_account_id = fields.Many2one('bank.account',
                                      u'结算账户', ondelete='restrict',
                                      help=u'用来核算和监督企业与其他单位或个人之间的债权债务的结算情况')
    debt = fields.Float(u'本次欠款', compute=_compute_all_amount, 
                        store=True, readonly=True, copy=False,
                        digits=dp.get_precision('Amount'),
                        help=u'本次欠款金额')
    total_debt = fields.Float(u'总欠款', compute=_compute_all_amount, 
                              store=True, readonly=True, copy=False,
                              digits=dp.get_precision('Amount'),
                              help=u'该客户的总欠款金额')
    cost_line_ids = fields.One2many('cost.line', 'sell_id', u'销售费用', 
                                    copy=False,
                                    help=u'销售费用明细行')
    money_state = fields.Char(u'收款状态', compute=_get_sell_money_state,
                              store=True, default=u'未收款',
                              help=u"销售发货单的收款状态", select=True, copy=False)
    return_state = fields.Char(u'退款状态', compute=_get_sell_return_state,
                               store=True, default=u'未退款',
                               help=u"销售退货单的退款状态", select=True, copy=False)
    contact = fields.Char(u'联系人', states=READONLY_STATES,
                          help=u'客户方的联系人')
    address = fields.Char(u'地址', states=READONLY_STATES,
                          help=u'联系地址')
    mobile = fields.Char(u'手机', states=READONLY_STATES,
                         help=u'联系手机')
    modifying = fields.Boolean(u'差错修改中', default=False,
                               help=u'是否处于差错修改中')

    @api.one
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''选择客户带出其默认地址信息'''
        if self.partner_id:
            self.contact = self.partner_id.contact
            self.address = self.partner_id.address
            self.mobile = self.partner_id.mobile

    @api.one
    @api.onchange('discount_rate', 'line_in_ids', 'line_out_ids')
    def onchange_discount_rate(self):
        '''当优惠率或订单行发生变化时，单据优惠金额发生变化'''
        total = 0
        if self.line_out_ids:
            # 发货时优惠前总金额
            total = sum(line.subtotal for line in self.line_out_ids)
        elif self.line_in_ids:
            # 退货时优惠前总金额
            total = sum(line.subtotal for line in self.line_in_ids)
        if self.discount_rate:
            self.discount_amount = total * self.discount_rate * 0.01

    def get_move_origin(self, vals):
        return self._name + (self.env.context.get('is_return') and '.return' 
                             or '.sell')

    @api.model
    def create(self, vals):
        '''创建销售发货单时生成有序编号'''
        if not self.env.context.get('is_return'):
            name = self._name
        else:
            name = 'sell.return'
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get(name) or '/'

        vals.update({
            'origin': self.get_move_origin(vals),
        })

        return super(sell_delivery, self).create(vals)

    @api.multi
    def unlink(self):
        for delivery in self:
            if delivery.state == 'done':
                raise except_orm(u'错误', u'不能删除已审核的单据')
            move = self.env['wh.move'].search(
                [('id', '=', delivery.sell_move_id.id)])
            if move:
                move.unlink()

        return super(sell_delivery, self).unlink()

    @api.one
    def check_goods_qty(self, goods, attribute, warehouse):
        '''SQL来取指定产品，属性，仓库，的当前剩余数量'''
        if attribute:
            self.env.cr.execute('''
                SELECT sum(line.qty_remaining) as qty
                FROM wh_move_line line
    
                WHERE line.warehouse_dest_id = %s
                  AND line.state = 'done'
                  AND line.attribute_id = %s
            ''' % (warehouse.id,attribute.id,))
    
            return self.env.cr.fetchone()
        elif goods:
            self.env.cr.execute('''
                SELECT sum(line.qty_remaining) as qty
                FROM wh_move_line line
    
                WHERE line.warehouse_dest_id = %s
                  AND line.state = 'done'
                  AND line.goods_id = %s
            ''' % (warehouse.id,goods.id,))
            
            return self.env.cr.fetchone()
        else:
            return False

    @api.multi
    def sell_delivery_done(self):
        '''审核销售发货单/退货单，更新本单的收款状态/退款状态，并生成源单和收款单'''
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        for line in self.line_in_ids:
            vals = {}
            if line.goods_qty <= 0 or line.price_taxed < 0:
                raise except_orm(u'错误', u'产品 %s 的数量和产品含税单价不能小于0！' % line.goods_id.name)
        for line in self.line_out_ids:
            vals={}
            result = False
            if line.goods_id.no_stock:
                continue
            else:
                result = self.check_goods_qty(line.goods_id, line.attribute_id, self.warehouse_id)
                if result[0]:
                    result = result[0][0] or 0
                else:
                    result = 0
            if line.goods_qty - result > 0 and not line.lot_id:
                #在销售出库时如果临时缺货，自动生成一张盘盈入库单
                vals.update({
                        'type':'inventory',
                        'warehouse_id':self.env.ref('warehouse.warehouse_inventory').id,
                        'warehouse_dest_id':self.warehouse_id.id,
                        'line_in_ids':[(0, 0, {
                                    'goods_id':line.goods_id.id,
                                    'attribute_id':line.attribute_id.id,
                                    'goods_uos_qty':line.goods_uos_qty - result/line.goods_id.conversion,
                                    'uos_id':line.uos_id.id,
                                    'goods_qty':line.goods_qty - result,
                                    'uom_id':line.uom_id.id,
                                    'cost_unit':line.goods_id.cost
                                                }
                                        )]
                            })
                msg = u'产品 %s 当前库存量不足，继续出售请点击确定，并及时盘点库存' % line.goods_id.name
                method = 'goods_inventery'
                dic = {
                    'name': u'警告',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'popup.wizard',
                    'type': 'ir.actions.act_window',
                    'context':{'method':method,
                               'vals':vals,
                               'msg':msg,},
                    'target': 'new',
                    }
                return dic
            if line.goods_qty <= 0 or line.price_taxed < 0:
                raise except_orm(u'错误', u'产品 %s 的数量和含税单价不能小于0！' % line.goods_id.name)
        if self.bank_account_id and not self.receipt:
            raise except_orm(u'警告！', u'结算账户不为空时，需要输入收款额！')
        if not self.bank_account_id and self.receipt:
            raise except_orm(u'警告！', u'收款额不为空时，请选择结算账户！')
        if self.receipt > self.amount + self.partner_cost:
            raise except_orm(u'警告！', u'本次收款金额不能大于优惠后金额！')
        if self.order_id:
            if not self.is_return:
                line_ids = self.line_out_ids
            else:
                line_ids = self.line_in_ids
            for line in line_ids:
                line.sell_line_id.quantity_out += line.goods_qty

        # 发库单/退货单 计算客户的 本次发货金额+客户应收余额 是否小于客户信用额度， 否则报错
        if not self.is_return:
            amount = self.amount + self.partner_cost
            if self.partner_id.credit_limit != 0:
                if amount - self.receipt + self.partner_id.receivable > self.partner_id.credit_limit:
                    raise except_orm(u'警告！', u'本次发货金额 + 客户应收余额 - 本次收款金额 不能大于客户信用额度！')
        else:
            amount = self.amount + self.partner_cost

        # 发库单/退货单 生成源单
        if not self.is_return:
            amount = self.amount + self.partner_cost
            this_reconcile = self.receipt
            tax_amount = sum(line.tax_amount for line in self.line_out_ids)
        else:
            amount = -(self.amount + self.partner_cost)
            this_reconcile = - self.receipt
            tax_amount = - sum(line.tax_amount for line in self.line_in_ids)
        categ = self.env.ref('money.core_category_sale')
        source_id = self.env['money.invoice'].create({
            'move_id': self.sell_move_id.id,
            'name': self.name,
            'partner_id': self.partner_id.id,
            'category_id': categ.id,
            'date': self.date,
            'amount': amount,
            'reconciled': 0,
            'to_reconcile': amount,
            'tax_amount': tax_amount,
            'date_due': self.date_due,
            'state': 'draft',
            'currency_id': self.currency_id.id
        })
        self.invoice_id = source_id.id
        # 销售费用产生源单
        if sum(cost_line.amount for cost_line in self.cost_line_ids) > 0:
            for line in self.cost_line_ids:
                cost_id = self.env['money.invoice'].create({
                    'move_id': self.sell_move_id.id,
                    'name': self.name,
                    'partner_id': line.partner_id.id,
                    'category_id': line.category_id.id,
                    'date': self.date,
                    'amount': line.amount,
                    'reconciled': 0.0,
                    'to_reconcile': line.amount,
                    'date_due': self.date_due,
                    'state': 'draft',
                    'currency_id': self.currency_id.id
                })
        # 生成收款单
        if self.receipt:
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
            rec = self.with_context(type='get')
            money_order = rec.env['money.order'].create({
                'partner_id': self.partner_id.id,
                'date': self.date,
                'line_ids': [(0, 0, line) for line in money_lines],
                'source_ids': [(0, 0, line) for line in source_lines],
                'type': 'get',
                'amount': amount,
                'reconciled': this_reconcile,
                'to_reconcile': amount,
                'state': 'draft',
            })
            money_order.money_order_done()

        # 调用wh.move中审核方法，更新审核人和审核状态
        self.sell_move_id.approve_order()
        # 生成分拆单 FIXME:无法跳转到新生成的分单
        if self.order_id and not self.modifying:
            return self.order_id.sell_generate_delivery()

        return True

    @api.one
    def sell_delivery_draft(self):
        '''反审核销售发货单/退货单，更新本单的收款状态/退款状态，并删除生成的源单、收款单及凭证'''
        # 查找产生的收款单
        source_line = self.env['source.order.line'].search(
                [('name', '=', self.invoice_id.id)])
        for line in source_line:
            line.money_id.money_order_draft()
            line.money_id.unlink()
        # 查找产生的源单
        invoice_ids = self.env['money.invoice'].search(
                [('name', '=', self.invoice_id.name)])
        for invoice in invoice_ids:
            invoice.money_invoice_draft()
            invoice.unlink()
        # 如果存在分单，则将差错修改中置为 True，再次审核时不生成分单
        self.modifying = False
        delivery_ids = self.search(
            [('order_id', '=', self.order_id.id)])
        if len(delivery_ids) > 1:
            self.modifying = True
        # 将源单中已执行数量清零
        order = self.env['sell.order'].search(
            [('id', '=', self.order_id.id)])
        for line in order.line_ids:
            line.quantity_out = 0
        # 调用wh.move中反审核方法，更新审核人和审核状态
        self.sell_move_id.cancel_approved_order()


class wh_move_line(models.Model):
    _inherit = 'wh.move.line'
    _description = u'销售发货单行'

    sell_line_id = fields.Many2one('sell.order.line', u'销货单行',
                                   ondelete='cascade',
                                   help=u'对应的销货订单行')

    @api.one
    @api.onchange('warehouse_id','goods_id')
    def onchange_warehouse_id(self):
        '''当订单行的仓库变化时，带出定价策略中的折扣率'''
        if self.warehouse_id and self.goods_id:
            partner_id = self.env.context.get('default_partner')
            partner = self.env['partner'].browse(partner_id) or self.move_id.partner_id
            warehouse = self.warehouse_id
            goods = self.goods_id
            date = self.env.context.get('default_date') or self.move_id.date
            if self.env.context.get('warehouse_type') == 'customer' or \
                    self.env.context.get('warehouse_dest_type') == 'customer':
                pricing = self.env['pricing'].get_pricing_id(partner,warehouse,goods,date)
            else:
                pricing = False
            if pricing:
                self.discount_rate = pricing.discount_rate
            else:
                self.discount_rate = 0

    @api.multi
    @api.onchange('goods_id')
    def onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的零售价，以及公司的销项税'''
        if self.goods_id:
            is_return = self.env.context.get('default_is_return')
            # 如果是销售发货单行 或 销售退货单行
            if (self.type == 'out' and not is_return) or (self.type == 'in' and is_return):
                self.tax_rate = self.env.user.company_id.output_tax_rate
                self.price_taxed = self.goods_id.price

        return super(wh_move_line,self).onchange_goods_id()

class cost_line(models.Model):
    _inherit = 'cost.line'

    sell_id = fields.Many2one('sell.delivery', u'出库单号',
                              ondelete='cascade',
                              help=u'与销售费用相关联的出库单号')


class money_invoice(models.Model):
    _inherit = 'money.invoice'


    move_id = fields.Many2one('wh.move', string=u'出入库单',
                              readonly=True, ondelete='cascade',
                              help=u'生成此发票的出入库单号')

class money_order(models.Model):
    _inherit = 'money.order'

    @api.multi
    def money_order_done(self):
        ''' 将已核销金额写回到销货订单中的已执行金额 '''
        res = super(money_order, self).money_order_done()
        move = False
        for source in self.source_ids:
            if self.type == 'get':
                move = self.env['sell.delivery'].search(
                    [('invoice_id', '=', source.name.id)])
                if move.order_id:
                    move.order_id.amount_executed = abs(source.name.reconciled)
        return res

    @api.multi
    def money_order_draft(self):
        ''' 将销货订单中的已执行金额清零'''
        res = super(money_order, self).money_order_draft()
        move = False
        for source in self.source_ids:
            if self.type == 'get':
                move = self.env['sell.delivery'].search(
                    [('invoice_id', '=', source.name.id)])
                if move.order_id:
                    move.order_id.amount_executed = 0
        return res


class sell_adjust(models.Model):
    _name = "sell.adjust"
    _inherit = ['mail.thread']
    _description = u"销售调整单"
    _order = 'date desc, id desc'

    name = fields.Char(u'单据编号', copy=False,
                       help=u'调整单编号，保存时可自动生成')
    order_id = fields.Many2one('sell.order', u'原始单据', states=READONLY_STATES,
                             copy=False, ondelete='restrict',
                             help=u'要调整的原始销货订单')
    date = fields.Date(u'单据日期', states=READONLY_STATES,
                       default=lambda self: fields.Date.context_today(self),
                       select=True, copy=False,
                       help=u'调整单创建日期，默认是当前日期')
    line_ids = fields.One2many('sell.adjust.line', 'order_id', u'调整单行',
                               states=READONLY_STATES, copy=True,
                               help=u'调整单明细行，不允许为空')
    approve_uid = fields.Many2one('res.users', u'审核人',
                            copy=False, ondelete='restrict',
                            help=u'审核调整单的人')
    state = fields.Selection(SELL_ORDER_STATES, u'审核状态',
                             select=True, copy=False,
                             default='draft',
                             help=u'调整单审核状态')
    note = fields.Text(u'备注',
                       help=u'单据备注')

    @api.multi
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise except_orm(u'错误', u'不能删除已审核的单据')

        return super(sell_adjust, self).unlink()

    @api.one
    def sell_adjust_done(self):
        '''审核销售调整单：
        当调整后数量 < 原单据中已出库数量，则报错；
        当调整后数量 > 原单据中已出库数量，则更新原单据及发货单分单的数量；
        当调整后数量 = 原单据中已出库数量，则更新原单据数量，删除发货单分单；
        当新增产品时，则更新原单据及发货单分单明细行。
        '''
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        if not self.line_ids:
            raise except_orm(u'错误', u'请输入产品明细行！')
        delivery = self.env['sell.delivery'].search(
                    [('order_id', '=', self.order_id.id),
                     ('state', '=', 'draft')])
        if not delivery:
            raise except_orm(u'错误', u'销售发货单已全部出库，不能调整')
        for line in self.line_ids:
            origin_line = self.env['sell.order.line'].search(
                        [('goods_id', '=', line.goods_id.id),
                         ('attribute_id', '=', line.attribute_id.id),
                         ('order_id', '=', self.order_id.id)])
            if len(origin_line) > 1:
                raise except_orm(u'错误', u'要调整的商品 %s 在原始单据中不唯一' % line.goods_id.name)
            if origin_line:
                origin_line.quantity += line.quantity # 调整后数量
                origin_line.note = line.note
                if origin_line.quantity < origin_line.quantity_out:
                    raise except_orm(u'错误', u' %s 调整后数量不能小于原订单已出库数量' % line.goods_id.name)
                elif origin_line.quantity > origin_line.quantity_out:
                    # 查找出原销货订单产生的草稿状态的发货单明细行，并更新它
                    move_line = self.env['wh.move.line'].search(
                                    [('sell_line_id', '=', origin_line.id),
                                     ('state', '=', 'draft')])
                    if move_line:
                        move_line.goods_qty += line.quantity
                        move_line.goods_uos_qty = move_line.goods_qty / move_line.goods_id.conversion
                        move_line.note = line.note
                    else:
                        raise except_orm(u'错误', u'商品 %s 已全部入库，建议新建购货订单' % line.goods_id.name)
                # 调整后数量与已出库数量相等时，删除产生的发货单分单
                else:
                    delivery.unlink()
            else:
                vals = {
                    'order_id': self.order_id.id,
                    'goods_id': line.goods_id.id,
                    'attribute_id': line.attribute_id.id,
                    'quantity': line.quantity,
                    'uom_id': line.uom_id.id,
                    'price_taxed': line.price_taxed,
                    'discount_rate': line.discount_rate,
                    'discount_amount': line.discount_amount,
                    'tax_rate': line.tax_rate,
                    'note': line.note or '',
                }
                new_line = self.env['sell.order.line'].create(vals)
                delivery_line = []
                if line.goods_id.force_batch_one:
                    i = 0
                    while i < line.quantity:
                        i += 1
                        delivery_line.append(
                                    self.order_id.get_delivery_line(new_line, single=True))
                else:
                    delivery_line.append(self.order_id.get_delivery_line(new_line, single=False))
                delivery.line_out_ids = [(0, 0, li[0]) for li in delivery_line]
        self.state = 'done'
        self.approve_uid = self._uid


class sell_adjust_line(models.Model):
    _name = 'sell.adjust.line'
    _description = u'销售调整单明细'

    @api.one
    @api.depends('goods_id')
    def _compute_using_attribute(self):
        '''返回订单行中产品是否使用属性'''
        self.using_attribute = self.goods_id.attribute_ids and True or False

    @api.one
    @api.depends('quantity', 'price_taxed', 'discount_amount', 'tax_rate')
    def _compute_all_amount(self):
        '''当订单行的数量、单价、折扣额、税率改变时，改变购货金额、税额、价税合计'''
        self.price = self.price_taxed / (1 + self.tax_rate * 0.01)
        self.amount = self.quantity * self.price - self.discount_amount  # 折扣后金额
        self.tax_amount = self.amount * self.tax_rate * 0.01  # 税额
        self.subtotal = self.amount + self.tax_amount

    order_id = fields.Many2one('sell.adjust', u'订单编号', select=True,
                               required=True, ondelete='cascade',
                               help=u'关联的调整单编号')
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
    quantity = fields.Float(u'调整数量', default=1,
                            digits=dp.get_precision('Quantity'),
                            help=u'相对于原单据对应明细行的调整数量，可正可负')
    price = fields.Float(u'销售单价', compute=_compute_all_amount,
                         store=True, readonly=True,
                         digits=dp.get_precision('Amount'),
                         help=u'不含税单价，由含税单价计算得出')
    price_taxed = fields.Float(u'含税单价',
                               digits=dp.get_precision('Amount'),
                               help=u'含税单价，取自商品零售价')
    discount_rate = fields.Float(u'折扣率%',
                         help=u'折扣率')
    discount_amount = fields.Float(u'折扣额',
                                   digits=dp.get_precision('Amount'),
                                   help=u'输入折扣率后自动计算得出，也可手动输入折扣额')
    amount = fields.Float(u'金额', compute=_compute_all_amount,
                          store=True, readonly=True,
                          digits=dp.get_precision('Amount'),
                          help=u'金额  = 价税合计  - 税额')
    tax_rate = fields.Float(u'税率(%)', default=lambda self:self.env.user.company_id.import_tax_rate,
                            help=u'默认值取公司销项税率')
    tax_amount = fields.Float(u'税额', compute=_compute_all_amount,
                              store=True, readonly=True,
                              digits=dp.get_precision('Amount'),
                              help=u'由税率计算得出')
    subtotal = fields.Float(u'价税合计', compute=_compute_all_amount,
                            store=True, readonly=True,
                            digits=dp.get_precision('Amount'),
                            help=u'含税单价 乘以 数量')
    note = fields.Char(u'备注',
                       help=u'本行备注')

    @api.one
    @api.onchange('goods_id')
    def onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的单位、默认仓库、价格'''
        if self.goods_id:
            self.uom_id = self.goods_id.uom_id
            self.price_taxed = self.goods_id.price

    @api.one
    @api.onchange('quantity', 'price_taxed', 'discount_rate')
    def onchange_discount_rate(self):
        '''当数量、含税单价或优惠率发生变化时，优惠金额发生变化'''
        price = self.price_taxed / (1 + self.tax_rate * 0.01)
        self.discount_amount = (self.quantity * price *
                                self.discount_rate * 0.01)
