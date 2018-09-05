# -*- coding: utf-8 -*-

from odoo import fields, models, api
import odoo.addons.decimal_precision as dp
import datetime
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
}
ISODATEFORMAT = '%Y-%m-%d'


class SellDelivery(models.Model):
    _name = 'sell.delivery'
    _inherits = {'wh.move': 'sell_move_id'}
    _inherit = ['mail.thread']
    _description = u'销售发货单'
    _order = 'date desc, id desc'

    @api.one
    @api.depends('line_out_ids.subtotal', 'discount_amount', 'partner_cost',
                 'receipt', 'partner_id', 'line_in_ids.subtotal')
    def _compute_all_amount(self):
        '''当优惠金额改变时，改变成交金额'''
        total = 0
        if self.line_out_ids:
            # 发货时优惠前总金
            total = sum(line.subtotal for line in self.line_out_ids)
        elif self.line_in_ids:
            # 退货时优惠前总金额
            total = sum(line.subtotal for line in self.line_in_ids)
        self.amount = total - self.discount_amount

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
    is_return = fields.Boolean(u'是否退货', default=lambda self:
                               self.env.context.get('is_return'),
                               help=u'是否为退货类型')
    order_id = fields.Many2one('sell.order', u'订单号', copy=False,
                               ondelete='cascade',
                               help=u'产生发货单/退货单的销货订单')
    invoice_id = fields.Many2one('money.invoice', u'发票号',
                                 copy=False, ondelete='set null',
                                 help=u'产生的发票号')
    date_due = fields.Date(u'到期日期', copy=False,
                           default=lambda self: fields.Date.context_today(
                               self),
                           help=u'收款截止日期')
    discount_rate = fields.Float(u'优惠率(%)', states=READONLY_STATES,
                                 help=u'整单优惠率')
    discount_amount = fields.Float(u'优惠金额', states=READONLY_STATES,
                                   digits=dp.get_precision('Amount'),
                                   help=u'整单优惠金额，可由优惠率自动计算得出，也可手动输入')
    amount = fields.Float(u'成交金额', compute=_compute_all_amount,
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
    address_id = fields.Many2one('partner.address', u'联系人地址', states=READONLY_STATES,
                                 help=u'联系地址')
    mobile = fields.Char(u'手机', states=READONLY_STATES,
                         help=u'联系手机')
    modifying = fields.Boolean(u'差错修改中', default=False,
                               help=u'是否处于差错修改中')
    origin_id = fields.Many2one('sell.delivery', u'来源单据')
    voucher_id = fields.Many2one('voucher', u'出库凭证', readonly=True,
                                 help=u'发货时产生的出库凭证')
    money_order_id = fields.Many2one(
        'money.order',
        u'收款单',
        readonly=True,
        copy=False,
        help=u'输入本次收款确认时产生的收款单')

    @api.onchange('address_id')
    def onchange_address_id(self):
        ''' 选择地址填充 联系人、电话 '''
        if self.address_id:
            self.contact = self.address_id.contact
            self.mobile = self.address_id.mobile

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''选择客户带出其默认地址信息'''
        if self.partner_id:
            self.contact = self.partner_id.contact
            self.mobile = self.partner_id.mobile

            for child in self.partner_id.child_ids:
                if child.is_default_add:
                    self.address_id = child.id
            if self.partner_id.child_ids and not any([child.is_default_add for child in self.partner_id.child_ids]):
                partners_add = self.env['partner.address'].search(
                    [('partner_id', '=', self.partner_id.id)], order='id')
                self.address_id = partners_add[0].id

            for line in self.line_out_ids:
                line.tax_rate = line.goods_id.get_tax_rate(line.goods_id, self.partner_id, 'sell')

            address_list = [
                child_list.id for child_list in self.partner_id.child_ids]
            if address_list:
                return {'domain': {'address_id': [('id', 'in', address_list)]}}
            else:
                self.address_id = False

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
            'finance_category_id': self.env.ref('finance.categ_sell_goods').id,
        })

        return super(SellDelivery, self).create(vals)

    @api.multi
    def unlink(self):
        for delivery in self:
            delivery.sell_move_id.unlink()

    def goods_inventory(self, vals):
        """
        审核时若仓库中商品不足，则产生补货向导生成其他入库单并审核。
        :param vals: 创建其他入库单需要的字段及取值信息构成的字典
        :return:
        """
        auto_in = self.env['wh.in'].create(vals)
        line_ids = [line.id for line in auto_in.line_in_ids]
        self.with_context({'wh_in_line_ids': line_ids}).sell_delivery_done()
        return True

    @api.one
    def _wrong_delivery_done(self):
        '''审核时不合法的给出报错'''
        if self.state == 'done':
            raise UserError(u'请不要重复发货')
        for line in self.line_in_ids:
            if line.goods_qty <= 0 or line.price_taxed < 0:
                raise UserError(u'商品 %s 的数量和商品含税单价不能小于0！' % line.goods_id.name)
        if not self.bank_account_id and self.receipt:
            raise UserError(u'收款额不为空时，请选择结算账户！')
        decimal_amount = self.env.ref('core.decimal_amount')
        if float_compare(self.receipt, self.amount + self.partner_cost, precision_digits=decimal_amount.digits) == 1:
            raise UserError(u'本次收款金额不能大于成交金额！\n本次收款金额:%s 成交金额:%s' %
                            (self.receipt, self.amount + self.partner_cost))
        # 发库单/退货单 计算客户的 本次发货金额+客户应收余额 是否小于客户信用额度， 否则报错
        if not self.is_return:
            amount = self.amount + self.partner_cost
            if self.partner_id.credit_limit != 0:
                if float_compare(amount - self.receipt + self.partner_id.receivable, self.partner_id.credit_limit,
                                 precision_digits=decimal_amount.digits) == 1:
                    raise UserError(u'本次发货金额 + 客户应收余额 - 本次收款金额 不能大于客户信用额度！\n\
                     本次发货金额:%s\n 客户应收余额:%s\n 本次收款金额:%s\n客户信用额度:%s' % (
                        amount, self.partner_id.receivable, self.receipt, self.partner_id.credit_limit))

    def _line_qty_write(self):
        if self.order_id:
            for line in self.line_in_ids:
                if self.order_id.type == 'return':
                    line.sell_line_id.quantity_out += line.goods_qty
                else:
                    line.sell_line_id.quantity_out -= line.goods_qty
            for line in self.line_out_ids:
                line.sell_line_id.write({'quantity_out':line.sell_line_id.quantity_out + line.goods_qty})

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
            'currency_id': self.currency_id.id,
            'note': self.note,
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
        if not float_is_zero(amount, 2):
            invoice_id = self.env['money.invoice'].create(
                self._get_invoice_vals(
                    self.partner_id, category, self.date, amount, tax_amount)
            )
        return invoice_id

    def _sell_amount_to_invoice(self):
        '''销售费用产生结算单'''
        invoice_id = False
        if sum(cost_line.amount for cost_line in self.cost_line_ids) > 0:
            for line in self.cost_line_ids:
                if not float_is_zero(line.amount, 2):
                    invoice_id = self.env['money.invoice'].create(
                        self._get_invoice_vals(
                            line.partner_id, line.category_id, self.date, line.amount + line.tax, line.tax)
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
            'amount': amount,
            'reconciled': this_reconcile,
            'to_reconcile': amount,
            'state': 'draft',
            'origin_name': self.name,
            'note': self.note,
            'sell_id': self.order_id.id,
        })
        return money_order

    def _create_voucher_line(self, account_id, debit, credit, voucher, goods_id, goods_qty):
        """
        创建凭证明细行
        :param account_id: 科目
        :param debit: 借方
        :param credit: 贷方
        :param voucher: 凭证
        :param goods_id: 商品
        :return:
        """
        voucher_line = self.env['voucher.line'].create({
            'name': u'%s %s' % (self.name, self.note or ''),
            'account_id': account_id and account_id.id,
            'debit': debit,
            'credit': credit,
            'voucher_id': voucher and voucher.id,
            'goods_qty': goods_qty,
            'goods_id': goods_id and goods_id.id,
        })
        return voucher_line

    @api.multi
    def create_voucher(self):
        '''
        销售发货单、退货单审核时生成会计凭证
        借：主营业务成本（核算分类上会计科目）
        贷：库存商品（商品分类上会计科目）

        当一张发货单有多个商品的时候，按对应科目汇总生成多个贷方凭证行。

        退货单生成的金额为负
        '''
        self.ensure_one()
        voucher = self.env['voucher'].create({'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})

        sum_amount = 0
        line_ids = self.is_return and self.line_in_ids or self.line_out_ids
        for line in line_ids:   # 发货单/退货单明细
            cost = self.is_return and -line.cost or line.cost
            if not cost:
                continue    # 缺货审核发货单时不产生出库凭证
            else:  # 贷方明细
                sum_amount += cost
                self._create_voucher_line(line.goods_id.category_id.account_id,
                                          0, cost, voucher, line.goods_id, line.goods_qty)
        if sum_amount:  # 借方明细
            self._create_voucher_line(self.sell_move_id.finance_category_id.account_id,
                                      sum_amount, 0, voucher, False, 0)

        if len(voucher.line_ids) > 0:
            voucher.voucher_done()
            return voucher
        else:
            voucher.unlink()

    @api.one
    def auto_reconcile_sell_order(self):
        ''' 预收款与结算单自动核销 '''
        all_delivery_amount = 0
        for delivery in self.order_id.delivery_ids:
            all_delivery_amount += delivery.amount

        if self.order_id.received_amount and self.order_id.received_amount == all_delivery_amount:
            adv_pay_result = []
            receive_source_result = []
            # 预收款
            adv_pay_orders = self.env['money.order'].search([('partner_id', '=', self.partner_id.id),
                                                             ('type', '=', 'get'),
                                                             ('state', '=', 'done'),
                                                             ('to_reconcile',
                                                              '!=', 0),
                                                             ('sell_id', '=', self.order_id.id)])
            for order in adv_pay_orders:
                adv_pay_result.append((0, 0, {'name': order.id,
                                              'amount': order.amount,
                                              'date': order.date,
                                              'reconciled': order.reconciled,
                                              'to_reconcile': order.to_reconcile,
                                              'this_reconcile': order.to_reconcile,
                                              }))
            # 结算单
            receive_source_name = [
                delivery.name for delivery in self.order_id.delivery_ids]
            receive_source_orders = self.env['money.invoice'].search([('category_id.type', '=', 'income'),
                                                                      ('partner_id', '=',
                                                                       self.partner_id.id),
                                                                      ('to_reconcile',
                                                                       '!=', 0),
                                                                      ('name', 'in', receive_source_name)])
            for invoice in receive_source_orders:
                receive_source_result.append((0, 0, {
                    'name': invoice.id,
                    'category_id': invoice.category_id.id,
                    'amount': invoice.amount,
                    'date': invoice.date,
                    'reconciled': invoice.reconciled,
                    'to_reconcile': invoice.to_reconcile,
                    'date_due': invoice.date_due,
                    'this_reconcile': invoice.to_reconcile,
                }))
            # 创建核销单
            reconcile_order = self.env['reconcile.order'].create({
                'partner_id': self.partner_id.id,
                'business_type': 'adv_pay_to_get',
                'advance_payment_ids': adv_pay_result,
                'receivable_source_ids': receive_source_result,
                'note': u'自动核销',
            })
            reconcile_order.reconcile_order_done()  # 自动审核

    @api.multi
    def sell_delivery_done(self):
        '''审核销售发货单/退货单，更新本单的收款状态/退款状态，并生成结算单和收款单'''
        for record in self:
            record._wrong_delivery_done()
            # 库存不足 生成零的
            if self.env.user.company_id.is_enable_negative_stock:
                result_vals = self.env['wh.move'].create_zero_wh_in(
                    record, record._name)
                if result_vals:
                    return result_vals
            # 调用wh.move中审核方法，更新审核人和审核状态
            record.sell_move_id.approve_order()
            # 将发货/退货数量写入销货订单行
            if record.order_id:
                record._line_qty_write()
            voucher = False
            # 创建出库的会计凭证，生成盘盈的入库单的不产生出库凭证
            if not self.env.user.company_id.endmonth_generation_cost:
                voucher = record.create_voucher()
            # 发货单/退货单 生成结算单
            invoice_id = record._delivery_make_invoice()
            # 销售费用产生结算单
            record._sell_amount_to_invoice()
            # 生成收款单，并审核
            money_order = False
            if record.receipt:
                flag = not record.is_return and 1 or -1
                amount = flag * (record.amount + record.partner_cost)
                this_reconcile = flag * record.receipt
                money_order = record._make_money_order(
                    invoice_id, amount, this_reconcile)
                money_order.money_order_done()

            record.write({
                'voucher_id': voucher and voucher.id,
                'invoice_id': invoice_id and invoice_id.id,
                'money_order_id': money_order and money_order.id,
                'state': 'done',  # 为保证审批流程顺畅，否则，未审批就可审核
            })

            # 先收款后发货订单自动核销
            self.auto_reconcile_sell_order()

            # 生成分拆单 FIXME:无法跳转到新生成的分单
            if record.order_id and not record.modifying:
                # 如果已退货也已退款，不生成新的分单
                if record.is_return and record.receipt:
                    return True
                return record.order_id.sell_generate_delivery()

    @api.one
    def sell_delivery_draft(self):
        '''反审核销售发货单/退货单，更新本单的收款状态/退款状态，并删除生成的结算单、收款单及凭证'''
        if self.state == 'draft':
            raise UserError(u'请不要重复撤销')
        # 查找产生的收款单
        source_line = self.env['source.order.line'].search(
            [('name', '=', self.invoice_id.id)])
        for line in source_line:
            if line.money_id.state == 'done':
                line.money_id.money_order_draft() # 反审核收款单
            # 判断收款单 源单行 是否有别的行存在
            other_source_line = []
            for s_line in line.money_id.source_ids:
                if s_line.id != line.id:
                    other_source_line.append(s_line)
            # 收款单 源单行 不存在别的行，删除收款单；否则删除收款单行，并对原收款单审核
            if not other_source_line:
                line.money_id.unlink()
            else:
                line.unlink()
                other_source_line[0].money_id.money_order_done()

            # FIXME:查找产生的核销单，反审核后删掉
        # 查找产生的结算单
        invoice_ids = self.env['money.invoice'].search(
            [('name', '=', self.invoice_id.name)])
        # 不能反审核已核销的发货单
        for invoice in invoice_ids:
            if invoice.to_reconcile == 0 and invoice.reconciled == invoice.amount:
                raise UserError(u'发货单已核销，不能撤销发货！')
        invoice_ids.money_invoice_draft()
        invoice_ids.unlink()
        # 删除产生的出库凭证
        voucher = self.voucher_id
        if voucher and voucher.state == 'done':
            voucher.voucher_draft()
        voucher.unlink()
        # 如果存在分单，则将差错修改中置为 True，再次审核时不生成分单
        self.write({
            'modifying': False,
            'state': 'draft',
        })
        delivery_ids = self.order_id and self.search(
            [('order_id', '=', self.order_id.id)]) or []
        if len(delivery_ids) > 1:
            self.write({
                'modifying': True,
                'state': 'draft',
            })
        # 将原始订单中已执行数量清零
        if self.order_id:
            for line in self.line_out_ids:
                line.sell_line_id.quantity_out -= line.goods_qty
            for line in self.line_in_ids:
                if self.order_id.type == 'return':
                    line.sell_line_id.quantity_out -= line.goods_qty
                else:
                    line.sell_line_id.quantity_out += line.goods_qty
        # 调用wh.move中反审核方法，更新审核人和审核状态
        self.sell_move_id.cancel_approved_order()

        return True

    @api.multi
    def sell_to_return(self):
        '''销售发货单转化为销售退货单'''
        return_goods = {}

        return_order_draft = self.search([
            ('is_return', '=', True),
            ('origin_id', '=', self.id),
            ('state', '=', 'draft')
        ])
        if return_order_draft:
            raise UserError(u'销售发货单存在草稿状态的退货单！')

        return_order = self.search([
            ('is_return', '=', True),
            ('origin_id', '=', self.id),
            ('state', '=', 'done')
        ])
        for order in return_order:
            for return_line in order.line_in_ids:
                # 用产品、属性、批次做key记录已退货数量
                t_key = (return_line.goods_id.id,
                         return_line.attribute_id.id, return_line.lot)
                if return_goods.get(t_key):
                    return_goods[t_key] += return_line.goods_qty
                else:
                    return_goods[t_key] = return_line.goods_qty
        receipt_line = []
        for line in self.line_out_ids:
            qty = line.goods_qty
            l_key = (line.goods_id.id, line.attribute_id.id, line.lot_id.lot)
            if return_goods.get(l_key):
                qty = qty - return_goods[l_key]
            if qty > 0:
                dic = {
                    'goods_id': line.goods_id.id,
                    'attribute_id': line.attribute_id.id,
                    'uom_id': line.uom_id.id,
                    'warehouse_id': line.warehouse_dest_id.id,
                    'warehouse_dest_id': line.warehouse_id.id,
                    'goods_qty': qty,
                    'sell_line_id': line.sell_line_id.id,
                    'price_taxed': line.price_taxed,
                    'price': line.price,
                    'tax_rate':line.tax_rate,
                    'cost_unit': line.cost_unit,
                    'cost': line.cost,#退货取不到成本
                    'discount_rate': line.discount_rate,
                    'discount_amount': line.discount_amount,
                    'type': 'in',
                }
                if line.goods_id.using_batch:
                    dic.update({'lot': line.lot_id.lot})
                receipt_line.append(dic)
        if len(receipt_line) == 0:
            raise UserError(u'该订单已全部退货！')
        vals = {'partner_id': self.partner_id.id,
                'is_return': True,
                'order_id': self.order_id.id,
                'origin_id': self.id,
                'origin': 'sell.delivery.return',
                'warehouse_dest_id': self.warehouse_id.id,
                'warehouse_id': self.warehouse_dest_id.id,
                'bank_account_id': self.bank_account_id.id,
                'date_due': (datetime.datetime.now()).strftime(ISODATEFORMAT),
                'date': (datetime.datetime.now()).strftime(ISODATEFORMAT),
                'line_in_ids': [(0, 0, line) for line in receipt_line],
                'discount_amount': self.discount_amount,
                }
        delivery_return = self.with_context(is_return=True).create(vals)
        view_id = self.env.ref('sell.sell_return_form').id
        name = u'销货退货单'
        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view_id, 'form')],
            'res_model': 'sell.delivery',
            'type': 'ir.actions.act_window',
            'res_id': delivery_return.id,
            'target': 'current'
        }


class WhMoveLine(models.Model):
    _inherit = 'wh.move.line'
    _description = u'销售发货单行'

    sell_line_id = fields.Many2one('sell.order.line', u'销货单行',
                                   ondelete='cascade',
                                   help=u'对应的销货订单行')

    @api.onchange('warehouse_id', 'goods_id')
    def onchange_warehouse_id(self):
        '''当订单行的仓库变化时，带出定价策略中的折扣率'''
        if self.warehouse_id and self.goods_id:
            partner_id = self.env.context.get('default_partner')
            partner = self.env['partner'].browse(
                partner_id) or self.move_id.partner_id
            warehouse = self.warehouse_id
            goods = self.goods_id
            date = self.env.context.get('default_date') or self.move_id.date
            if self.env.context.get('warehouse_type') == 'customer' or \
                    self.env.context.get('warehouse_dest_type') == 'customer':
                pricing = self.env['pricing'].get_pricing_id(
                    partner, warehouse, goods, date)
                if pricing:
                    self.discount_rate = pricing.discount_rate
                else:
                    self.discount_rate = 0

    def _delivery_get_price_and_tax(self):
        self.tax_rate = self.env.user.company_id.output_tax_rate
        self.price_taxed = self.goods_id.price

    @api.multi
    @api.onchange('goods_id')
    def onchange_goods_id(self):
        '''当订单行的商品变化时，带出商品上的零售价，以及公司的销项税'''
        self.ensure_one()
        is_return = self.env.context.get('default_is_return')
        if self.goods_id:
            # 如果是销售发货单行 或 销售退货单行
            if is_return is not None and \
                    ((self.type == 'out' and not is_return) or (self.type == 'in' and is_return)):
                self._delivery_get_price_and_tax()

        return super(WhMoveLine, self).onchange_goods_id()
