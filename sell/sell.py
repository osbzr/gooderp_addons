# -*- encoding: utf-8 -*-

from openerp import fields, models, api
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

    partner_id = fields.Many2one('partner', u'客户', states=READONLY_STATES)
    staff_id = fields.Many2one('staff', u'销售员', states=READONLY_STATES)
    date = fields.Date(u'单据日期', states=READONLY_STATES,
                       default=lambda self: fields.Date.context_today(self),
                       select=True, copy=False, help=u"默认是订单创建日期")
    delivery_date = fields.Date(u'要求交货日期', states=READONLY_STATES,
                                default=lambda self: fields.Date.context_today(self),
                                select=True, copy=False, help=u"订单的要求交货日期")
    type = fields.Selection([('sell', u'销货'), ('return', u'退货')], u'类型', default='sell', states=READONLY_STATES)
    name = fields.Char(u'单据编号', select=True, copy=False,
                       default='/', help=u"创建时它会自动生成下一个编号")
    line_ids = fields.One2many('sell.order.line', 'order_id', u'销货订单行',
                               states=READONLY_STATES, copy=True)
    note = fields.Text(u'备注')
    discount_rate = fields.Float(u'优惠率(%)', states=READONLY_STATES)
    discount_amount = fields.Float(u'优惠金额', states=READONLY_STATES, track_visibility='always')
    amount = fields.Float(string=u'优惠后金额', store=True, readonly=True,
                          compute='_compute_amount', track_visibility='always')
    approve_uid = fields.Many2one('res.users', u'审核人', copy=False)
    state = fields.Selection(SELL_ORDER_STATES, u'审核状态', readonly=True,
                             help=u"销货订单的审核状态", select=True, copy=False, default='draft')
    goods_state = fields.Char(u'发货状态', compute=_get_sell_goods_state,
                              help=u"销货订单的发货状态", select=True, copy=False)
    cancelled = fields.Boolean(u'已终止')

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
    def sell_order_done(self):
        '''审核销货订单'''
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        if not self.line_ids:
            raise except_orm(u'错误', u'请输入产品明细行！')
        # TODO:销售预收款
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
            delivery = self.env['sell.delivery'].search([('order_id', '=', self.name)])
            if delivery:
                delivery.unlink()
        self.state = 'draft'
        self.approve_uid = ''

    @api.one
    def get_delivery_line(self, line, single=False):
        # TODO：如果退货，warehouse_dest_id，warehouse_id要调换
        qty = 0
        discount_amount = 0
        if single:
            qty = 1
            discount_amount = line.discount_amount / (line.quantity - line.quantity_out)
        else:
            qty = line.quantity - line.quantity_out
            discount_amount = line.discount_amount
        if self.type == 'sell':
            warehouse_id = line.warehouse_id.id
            warehouse_dest_id = line.warehouse_dest_id.id
        # 如果退货，调换warehouse_dest_id，warehouse_id
        elif self.type == 'return':
            warehouse_id = line.warehouse_dest_id.id
            warehouse_dest_id = line.warehouse_id.id
        return {
            'sell_line_id': line.id,
            'goods_id': line.goods_id.id,
            'attribute_id': line.attribute_id.id,
            'uom_id': line.uom_id.id,
            'warehouse_id': warehouse_id,
            'warehouse_dest_id': warehouse_dest_id,
            'goods_qty': qty,
            'price': line.price,
            'discount_rate': line.discount_rate,
            'discount_amount': discount_amount,
            'tax_rate': line.tax_rate,
            'note': line.note or '',
        }

    @api.one
    def sell_generate_delivery(self):
        '''由销货订单生成销售发货单'''
        delivery_line = []  # 销售发货单行

        for line in self.line_ids:
            # 如果订单部分出库，则点击此按钮时生成剩余数量的出库单
            to_out = line.quantity - line.quantity_out
            if to_out == 0:
                continue
            if line.goods_id.force_batch_one:
                i = 0
                while i < to_out:
                    i += 1
                    delivery_line.append(self.get_delivery_line(line, single=True))
            else:
                delivery_line.append(self.get_delivery_line(line, single=False))

        if not delivery_line:
            return {}
        if self.type == 'sell':
            delivery_id = self.env['sell.delivery'].create({
                'partner_id': self.partner_id.id,
                'staff_id': self.staff_id.id,
                'date': self.delivery_date,
                'order_id': self.id,
                'origin': 'sell.delivery',
                'line_out_ids': [(0, 0, line[0]) for line in delivery_line],
                'note': self.note,
                'discount_rate': self.discount_rate,
                'discount_amount': self.discount_amount,
            })
            view_id = self.env['ir.model.data'].xmlid_to_res_id('sell.sell_delivery_form')
            name = u'销售发货单'
        elif self.type == 'return':
            rec = self.with_context(is_return=True)
            delivery_id = rec.env['sell.delivery'].create({
                'partner_id': self.partner_id.id,
                'staff_id': self.staff_id.id,
                'date': self.delivery_date,
                'order_id': self.id,
                'origin': 'sell.delivery',
                'line_in_ids': [(0, 0, line[0]) for line in delivery_line],
                'note': self.note,
                'discount_rate': self.discount_rate,
                'discount_amount': self.discount_amount,
            })
            view_id = self.env['ir.model.data'].xmlid_to_res_id('sell.sell_return_form')
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

    @api.model
    def _default_warehouse_dest(self):
        context = self._context or {}
        if context.get('warehouse_dest_type'):
            return self.env['warehouse'].get_warehouse_by_type(context.get('warehouse_dest_type'))

        return False

    @api.one
    @api.depends('quantity', 'price', 'discount_amount', 'tax_rate')
    def _compute_all_amount(self):
        '''当订单行的数量、单价、折扣额、税率改变时，改变销售金额、税额、价税合计'''
        amount = self.quantity * self.price - self.discount_amount  # 折扣后金额
        tax_amt = amount * self.tax_rate * 0.01  # 税额
        self.price_taxed = self.price * (1 + self.tax_rate * 0.01)
        self.amount = amount
        self.tax_amount = tax_amt
        self.subtotal = amount + tax_amt

    order_id = fields.Many2one('sell.order', u'订单编号', select=True, required=True, ondelete='cascade')
    goods_id = fields.Many2one('goods', u'商品')
    attribute_id = fields.Many2one('attribute', u'属性', domain="[('goods_id', '=', goods_id)]")
    uom_id = fields.Many2one('uom', u'单位')
    warehouse_id = fields.Many2one('warehouse', u'仓库')
    warehouse_dest_id = fields.Many2one('warehouse', u'调入仓库', default=_default_warehouse_dest)
    quantity = fields.Float(u'数量', default=1)
    quantity_out = fields.Float(u'已发货数量', copy=False)
    price = fields.Float(u'销售单价')
    price_taxed = fields.Float(u'含税单价', compute=_compute_all_amount, store=True, readonly=True)
    discount_rate = fields.Float(u'折扣率%')
    discount_amount = fields.Float(u'折扣额')
    amount = fields.Float(u'金额', compute=_compute_all_amount, store=True, readonly=True)
    tax_rate = fields.Float(u'税率(%)', default=17.0)
    tax_amount = fields.Float(u'税额', compute=_compute_all_amount, store=True, readonly=True)
    subtotal = fields.Float(u'价税合计', compute=_compute_all_amount, store=True, readonly=True)
    note = fields.Char(u'备注')

    @api.one
    @api.onchange('goods_id')
    def onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的单位、默认仓库、价格'''
        if self.goods_id:
            self.uom_id = self.goods_id.uom_id
            self.warehouse_id = self.goods_id.default_wh  # 取产品的默认仓库
            matched = False # 在商品的价格清单中是否找到匹配的价格
            for line in self.goods_id.price_ids:
                if self.order_id.partner_id.c_category_id == line.category_id:
                    self.price = line.price
                    matched = True

            if not matched:
                raise except_orm(u'错误', u'请先设置商品的价格清单或客户类别！')

    @api.one
    @api.onchange('quantity', 'price', 'discount_rate')
    def onchange_discount_rate(self):
        '''当数量、单价或优惠率发生变化时，优惠金额发生变化'''
        self.discount_amount = self.quantity * self.price * self.discount_rate * 0.01


class sell_delivery(models.Model):
    _name = 'sell.delivery'
    _inherits = {'wh.move': 'sell_move_id'}
    _inherit = ['mail.thread']
    _description = u'销售发货单'
    _order = 'date desc, id desc'

    @api.one
    @api.depends('line_out_ids.subtotal', 'discount_amount', 'partner_cost', 'receipt', 'partner_id', 'line_in_ids.subtotal')
    def _compute_all_amount(self):
        '''当优惠金额改变时，改变优惠后金额、本次欠款和总欠款'''
        total = 0
        if self.line_out_ids:
            total = sum(line.subtotal for line in self.line_out_ids)  # 发货时优惠前总金额
        elif self.line_in_ids:
            total = sum(line.subtotal for line in self.line_in_ids)  # 退货时优惠前总金额
        self.amount = total - self.discount_amount
        self.debt = self.amount - self.receipt + self.partner_cost
        self.total_debt = self.partner_id.receivable + self.debt    # 本次欠款变化时，总欠款应该变化

    @api.one
    @api.depends('state', 'amount', 'receipt')
    def _get_sell_money_state(self):
        '''返回收款状态'''
        if not self.is_return:
            if self.state == 'draft':
                self.money_state = u'未收款'
            else:
                if self.receipt == 0:
                    self.money_state = u'未收款'
                elif self.amount > self.receipt:
                    self.money_state = u'部分收款'
                elif self.amount == self.receipt:
                    self.money_state = u'全部收款'

    @api.one
    @api.depends('state', 'amount', 'receipt')
    def _get_sell_return_state(self):
        '''返回退款状态'''
        if self.is_return:
            if self.state == 'draft':
                self.return_state = u'未退款'
            else:
                if self.receipt == 0:
                    self.return_state = u'未退款'
                elif self.amount > self.receipt:
                    self.return_state = u'部分退款'
                elif self.amount == self.receipt:
                    self.return_state = u'全部退款'

    sell_move_id = fields.Many2one('wh.move', u'发货单', required=True, ondelete='cascade')
    is_return = fields.Boolean(u'是否退货', default=lambda self: self.env.context.get('is_return'))
    staff_id = fields.Many2one('staff', u'销售员')
    order_id = fields.Many2one('sell.order', u'源单号', copy=False)
    invoice_id = fields.Many2one('money.invoice', u'发票号', copy=False)
    date_due = fields.Date(u'到期日期', copy=False)
    discount_rate = fields.Float(u'优惠率(%)', states=READONLY_STATES)
    discount_amount = fields.Float(u'优惠金额', states=READONLY_STATES)
    amount = fields.Float(u'优惠后金额', compute=_compute_all_amount, store=True, readonly=True)
    partner_cost = fields.Float(u'客户承担费用')
    receipt = fields.Float(u'本次收款', states=READONLY_STATES)
    bank_account_id = fields.Many2one('bank.account', u'结算账户')
    debt = fields.Float(u'本次欠款', compute=_compute_all_amount, store=True, readonly=True, copy=False)
    total_debt = fields.Float(u'总欠款', compute=_compute_all_amount, store=True, readonly=True, copy=False)
    cost_line_ids = fields.One2many('cost.line', 'sell_id', u'销售费用', copy=False)
    money_state = fields.Char(u'收款状态', compute=_get_sell_money_state,
                              help=u"销售发货单的收款状态", select=True, copy=False)
    return_state = fields.Char(u'退款状态', compute=_get_sell_return_state,
                               help=u"销售退货单的退款状态", select=True, copy=False)

    @api.one
    @api.onchange('discount_rate', 'line_in_ids', 'line_out_ids')
    def onchange_discount_rate(self):
        '''当优惠率或订单行发生变化时，单据优惠金额发生变化'''
        total = 0
        if self.line_out_ids:
            total = sum(line.subtotal for line in self.line_out_ids)  # 发货时优惠前总金额
        elif self.line_in_ids:
            total = sum(line.subtotal for line in self.line_in_ids)  # 退货时优惠前总金额
        if self.discount_rate:
            self.discount_amount = total * self.discount_rate * 0.01

    def get_move_origin(self, vals):
        return self._name + (self.env.context.get('is_return') and '.return' or '.sell')

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
            move = self.env['wh.move'].search([('id', '=', delivery.sell_move_id.id)])
            if move:
                move.unlink()

        return super(sell_delivery, self).unlink()

    @api.one
    def sell_delivery_done(self):
        '''审核销售发货单/退货单，更新本单的收款状态/退款状态，并生成源单和收款单'''
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        if self.bank_account_id and not self.receipt:
            raise except_orm(u'警告！', u'结算账户不为空时，需要输入付款额！')
        if not self.bank_account_id and self.receipt:
            raise except_orm(u'警告！', u'付款额不为空时，请选择结算账户！')
        if self.receipt > self.amount:
            raise except_orm(u'警告！', u'本次收款金额不能大于优惠后金额！')

        if self.order_id:
            if not self.is_return:
                line_ids = self.line_out_ids
            else:
                line_ids = self.line_in_ids
            for line in line_ids:
                line.sell_line_id.quantity_out += line.goods_qty

        # 发库单/退货单 生成源单
        if not self.is_return:
            amount = self.amount + self.partner_cost
            this_reconcile = self.receipt
        else:
            amount = -(self.amount + self.partner_cost)
            this_reconcile = - self.receipt
        categ = self.env.ref('money.core_category_sale')
        source_id = self.env['money.invoice'].create({
            'move_id': self.sell_move_id.id,
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
        # 销售费用产生源单
        if sum(cost_line.amount for cost_line in self.cost_line_ids) > 0:
            for line in self.cost_line_ids:
                cost_id = self.env['money.invoice'].create({
                    'move_id': self.sell_move_id.id,
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
                'date': fields.Date.context_today(self),
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
        if self.order_id:
            return self.order_id.sell_generate_delivery()

        return True


class sell_delivery_line(models.Model):
    _inherit = 'wh.move.line'
    _description = u'销售发货单行'

    sell_line_id = fields.Many2one('sell.order.line', u'销货单行')
    origin = fields.Char(u'源单号')


class cost_line(models.Model):
    _inherit = 'cost.line'

    sell_id = fields.Many2one('sell.delivery', u'出库单号')


class money_invoice(models.Model):
    _inherit = 'money.invoice'

    move_id = fields.Many2one('wh.move', string=u'出入库单', readonly=True)
