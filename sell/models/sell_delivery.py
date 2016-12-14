# -*- encoding: utf-8 -*-

from odoo import fields, models, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
}


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
        # 返回退款状态
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
    order_id = fields.Many2one('sell.order', u'订单号', copy=False,
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
                              help=u"销售发货单的收款状态", index=True, copy=False)
    return_state = fields.Char(u'退款状态', compute=_get_sell_money_state,
                               store=True, default=u'未退款',
                               help=u"销售退货单的退款状态", index=True, copy=False)
    contact = fields.Char(u'联系人', states=READONLY_STATES,
                          help=u'客户方的联系人')
    address = fields.Char(u'地址', states=READONLY_STATES,
                          help=u'联系地址')
    mobile = fields.Char(u'手机', states=READONLY_STATES,
                         help=u'联系手机')
    modifying = fields.Boolean(u'差错修改中', default=False,
                               help=u'是否处于差错修改中')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''选择客户带出其默认地址信息'''
        if self.partner_id:
            self.contact = self.partner_id.contact
            self.address = self.partner_id.address
            self.mobile = self.partner_id.mobile

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
            vals['name'] = self.env['ir.sequence'].next_by_code(name) or '/'

        vals.update({
            'origin': self.get_move_origin(vals),
        })

        return super(sell_delivery, self).create(vals)

    @api.multi
    def unlink(self):
        for delivery in self:
            if delivery.state == 'done':
                raise UserError(u'不能删除已审核的销售发货单')
            delivery.sell_move_id.unlink()

        return super(sell_delivery, self).unlink()

    def goods_inventory(self, vals):
        auto_in = self.env['wh.in'].create(vals)
        line_ids = [line.id for line in auto_in.line_in_ids]
        self.with_context({'wh_in_line_ids':line_ids}).sell_delivery_done()

    @api.one
    def _wrong_delivery_done(self):
        '''审核时不合法的给出报错'''
        if self.state == 'done':
            raise UserError(u'请不要重复审核！')
        for line in self.line_in_ids:
            if line.goods_qty <= 0 or line.price_taxed < 0:
                raise UserError(u'产品 %s 的数量和产品含税单价不能小于0！' % line.goods_id.name)
        if not self.bank_account_id and self.receipt:
            raise UserError(u'收款额不为空时，请选择结算账户！')
        if self.receipt > self.amount + self.partner_cost:
            raise UserError(u'本次收款金额不能大于优惠后金额！\n本次收款金额:%s 优惠后金额:%s' %
                            (self.receipt, self.amount + self.partner_cost))
        # 发库单/退货单 计算客户的 本次发货金额+客户应收余额 是否小于客户信用额度， 否则报错
        if not self.is_return:
            amount = self.amount + self.partner_cost
            if self.partner_id.credit_limit != 0:
                if amount - self.receipt + self.partner_id.receivable > self.partner_id.credit_limit:
                    raise UserError(u'本次发货金额 + 客户应收余额 - 本次收款金额 不能大于客户信用额度！\n\
                     本次发货金额:%s\n 客户应收余额:%s\n 本次收款金额:%s\n客户信用额度:%s' % (
                    amount, self.receipt, self.partner_id.receivable, self.partner_id.credit_limit))

    def _line_qty_write(self):
        line_ids = not self.is_return and self.line_out_ids or self.line_in_ids
        for line in line_ids:
            line.sell_line_id.quantity_out += line.goods_qty

        return

    def _get_invoice_vals(self, partner_id, category_id, date, amount, tax_amount):
        '''返回创建 money_invoice 时所需数据'''
        return {
            'move_id': self.sell_move_id.id,
            'name': self.name,
            'partner_id': partner_id.id,
            'category_id': category_id.id,
            'date': date,
            'amount': amount,
            'reconciled': 0,
            'to_reconcile': amount,
            'tax_amount': tax_amount,
            'date_due': self.date_due,
            'state': 'draft',
            'currency_id': self.currency_id.id
        }

    def _delivery_make_invoice(self):
        '''发货单/退货单 生成结算单'''
        if not self.is_return:
            amount = self.amount + self.partner_cost
            tax_amount = sum(line.tax_amount for line in self.line_out_ids)
        else:
            amount = -(self.amount + self.partner_cost)
            tax_amount = - sum(line.tax_amount for line in self.line_in_ids)
        category = self.env.ref('money.core_category_sale')
        invoice_id = False
        if not float_is_zero(amount,2):
            invoice_id = self.env['money.invoice'].create(
                self._get_invoice_vals(self.partner_id, category, self.date, amount, tax_amount)
            )
            self.invoice_id = invoice_id.id
        return invoice_id

    def _sell_amount_to_invoice(self):
        '''销售费用产生结算单'''
        invoice_id = False
        if sum(cost_line.amount for cost_line in self.cost_line_ids) > 0:
            for line in self.cost_line_ids:
                if not float_is_zero(line.amount,2):
                    invoice_id = self.env['money.invoice'].create(
                        self._get_invoice_vals(line.partner_id, line.category_id, self.date, line.amount + line.tax, line.tax)
                    )
        return invoice_id

    def _make_money_order(self, invoice_id, amount, this_reconcile):
        '''生成收款单'''
        categ = self.env.ref('money.core_category_sale')
        money_lines = [{
            'bank_id': self.bank_account_id.id,
            'amount': this_reconcile,
        }]
        source_lines = [{
            'name': invoice_id and invoice_id.id,
            'category_id': categ.id,
            'date': invoice_id and invoice_id.date,
            'amount': amount,
            'reconciled': 0.0,
            'to_reconcile': amount,
            'this_reconcile': this_reconcile,
        }]
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
        return money_order

    @api.multi
    def sell_delivery_done(self):
        '''审核销售发货单/退货单，更新本单的收款状态/退款状态，并生成结算单和收款单'''
        for record in self:
            record._wrong_delivery_done()
            # 库存不足 生成零的
            result_vals = self.env['wh.move'].create_zero_wh_in(record,record._name)
            if result_vals:
                return result_vals
            # 调用wh.move中审核方法，更新审核人和审核状态
            record.sell_move_id.approve_order()
            #将发货/退货数量写入销货订单行
            if record.order_id:
                record._line_qty_write()
            # 发货单/退货单 生成结算单
            invoice_id = record._delivery_make_invoice()
            # 销售费用产生结算单
            record._sell_amount_to_invoice()
            # 生成收款单，并审核
            if record.receipt:
                flag = not record.is_return and 1 or -1
                amount = flag * (record.amount + record.partner_cost)
                this_reconcile = flag * record.receipt
                money_order = record._make_money_order(invoice_id, amount, this_reconcile)
                money_order.money_order_done()

            # 生成分拆单 FIXME:无法跳转到新生成的分单
            if record.order_id and not record.modifying:
                return record.order_id.sell_generate_delivery()

    @api.one
    def sell_delivery_draft(self):
        '''反审核销售发货单/退货单，更新本单的收款状态/退款状态，并删除生成的结算单、收款单及凭证'''
        # 查找产生的收款单
        source_line = self.env['source.order.line'].search(
                [('name', '=', self.invoice_id.id)])
        for line in source_line:
            line.money_id.money_order_draft()
            line.money_id.unlink()
            # FIXME:查找产生的核销单，反审核后删掉
        # 查找产生的结算单
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
        # 将原始订单中已执行数量清零
        if self.order_id:
            line_ids = not self.is_return and self.line_in_ids or self.line_out_ids
            for line in line_ids:
                line.sell_line_id.quantity_out -= line.goods_qty
        # 调用wh.move中反审核方法，更新审核人和审核状态
        self.sell_move_id.cancel_approved_order()


class wh_move_line(models.Model):
    _inherit = 'wh.move.line'
    _description = u'销售发货单行'

    sell_line_id = fields.Many2one('sell.order.line', u'销货单行',
                                   ondelete='cascade',
                                   help=u'对应的销货订单行')

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
                if pricing:
                    self.discount_rate = pricing.discount_rate
                else:
                    self.discount_rate = 0

    def _delivery_get_price_and_tax(self):
        self.tax_rate = self.env.user.company_id.output_tax_rate
        self.price_taxed = self.goods_id.price

    @api.multi
    @api.onchange('goods_id', 'tax_rate')
    def onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的零售价，以及公司的销项税'''
        self.ensure_one()
        if self.goods_id:
            is_return = self.env.context.get('default_is_return')
            # 如果是销售发货单行 或 销售退货单行
            if (self.type == 'out' and not is_return) or (self.type == 'in' and is_return):
                self._delivery_get_price_and_tax()

        return super(wh_move_line,self).onchange_goods_id()
