# -*- coding: utf-8 -*-

from odoo import fields, models, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tools import float_compare, float_is_zero

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
}


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
        # 返回退款状态
        if self.is_return:
            if self.invoice_id.reconciled == 0:
                self.return_state = u'未退款'
            elif abs(self.invoice_id.reconciled) < abs(self.invoice_id.amount):
                self.return_state = u'部分退款'
            elif self.invoice_id.reconciled == self.invoice_id.amount:
                self.return_state = u'全部退款'

    buy_move_id = fields.Many2one('wh.move', u'入库单',
                                  required=True, ondelete='cascade',
                                  help=u'入库单号')
    is_return = fields.Boolean(u'是否退货',
                    default=lambda self: self.env.context.get('is_return'),
                    help=u'是否为退货类型')
    order_id = fields.Many2one('buy.order', u'订单号',
                               copy=False, ondelete='cascade',
                               help=u'产生入库单/退货单的购货订单')
    invoice_id = fields.Many2one('money.invoice', u'发票号', copy=False,
                                 ondelete='set null',
                                 help=u'产生的发票号')
    date_due = fields.Date(u'到期日期', copy=False,
                           default=lambda self: fields.Date.context_today(self),
                           help=u'付款截止日期')
    discount_rate = fields.Float(u'优惠率(%)', states=READONLY_STATES,
                                 help=u'整单优惠率')
    discount_amount = fields.Float(u'优惠金额', states=READONLY_STATES,
                                   digits=dp.get_precision('Amount'),
                                   help=u'整单优惠金额，可由优惠率自动计算得出，也可手动输入')
    invoice_by_receipt=fields.Boolean(string=u"按收货结算", default=True,
                                      help=u'如未勾选此项，可在资金行里输入付款金额，订单保存后，采购人员可以单击资金行上的【确认】按钮。')
    amount = fields.Float(u'优惠后金额', compute=_compute_all_amount,
                          store=True, readonly=True,
                          digits=dp.get_precision('Amount'),
                          help=u'总金额减去优惠金额')
    payment = fields.Float(u'本次付款', states=READONLY_STATES,
                           digits=dp.get_precision('Amount'),
                           help=u'本次付款金额')
    bank_account_id = fields.Many2one('bank.account', u'结算账户', 
                                      ondelete='restrict',
                                      help=u'用来核算和监督企业与其他单位或个人之间的债权债务的结算情况')
    debt = fields.Float(u'本次欠款', compute=_compute_all_amount,
                        store=True, readonly=True, copy=False,
                        digits=dp.get_precision('Amount'),
                        help=u'本次欠款金额')
    cost_line_ids = fields.One2many('cost.line', 'buy_id', u'采购费用', copy=False,
                                    help=u'采购费用明细行')
    money_state = fields.Char(u'付款状态', compute=_get_buy_money_state,
                              store=True, default=u'未付款',
                              help=u"采购入库单的付款状态",
                              index=True, copy=False)
    return_state = fields.Char(u'退款状态', compute=_get_buy_money_state,
                               store=True, default=u'未退款',
                               help=u"采购退货单的退款状态",
                               index=True, copy=False)
    modifying = fields.Boolean(u'差错修改中', default=False,
                               help=u'是否处于差错修改中')
    voucher_id = fields.Many2one('voucher', u'入库凭证', readonly=True,
                                 help=u'审核时产生的入库凭证')

    def _compute_total(self, line_ids):
        return sum(line.subtotal for line in line_ids)

    @api.onchange('discount_rate', 'line_in_ids', 'line_out_ids')
    def onchange_discount_rate(self):
        '''当优惠率或订单行发生变化时，单据优惠金额发生变化'''
        line = self.line_in_ids or self.line_out_ids
        total = self._compute_total(line)
        if self.discount_rate:
            self.discount_amount = total * self.discount_rate * 0.01

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            for line in self.line_in_ids:
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
            vals['name'] = self.env['ir.sequence'].next_by_code(name) or '/'

        vals.update({
            'origin': self.get_move_origin(vals)
        })
        return super(buy_receipt, self).create(vals)

    @api.multi
    def unlink(self):
        for receipt in self:
            if receipt.state == 'done':
                raise UserError(u'不能删除已审核的单据')
            receipt.buy_move_id.unlink()

        return super(buy_receipt, self).unlink()

    @api.one
    def _wrong_receipt_done(self):
        if self.state == 'done':
            raise UserError(u'请不要重复审核！')
        batch_one_list_wh = []
        batch_one_list = []
        for line in self.line_in_ids:
            if line.goods_id.force_batch_one:
                wh_move_lines = self.env['wh.move.line'].search([('state', '=', 'done'), ('type', '=', 'in'), ('goods_id', '=', line.goods_id.id)])
                for move_line in wh_move_lines:
                    if (move_line.goods_id.id, move_line.lot) not in batch_one_list_wh and move_line.lot:
                        batch_one_list_wh.append((move_line.goods_id.id, move_line.lot))

            if (line.goods_id.id, line.lot) in batch_one_list_wh:
                raise UserError(u'仓库已存在相同序列号的产品！\n产品:%s 序列号:%s'%(line.goods_id.name,line.lot))

        for line in self.line_in_ids:
            if line.goods_qty <= 0 or line.price_taxed < 0:
                raise UserError(u'产品 %s 的数量和含税单价不能小于0！' % line.goods_id.name)
            if line.goods_id.force_batch_one:
                batch_one_list.append((line.goods_id.id, line.lot))

        if len(batch_one_list) > len(set(batch_one_list)):
            raise UserError(u'不能创建相同序列号的产品！\n 序列号list为%s'%str(batch_one_list))

        for line in self.line_out_ids:
            if line.goods_qty <= 0 or line.price_taxed < 0:
                raise UserError(u'产品 %s 的数量和含税单价不能小于0！' % line.goods_id.name)
        
        if not self.bank_account_id and self.payment:
            raise UserError(u'付款额不为空时，请选择结算账户！')
        decimal_amount = self.env.ref('core.decimal_amount')
        if float_compare(self.payment, self.amount, precision_digits=decimal_amount.digits) == 1:
            raise UserError(u'本次付款金额不能大于折后金额！\n付款金额:%s 折后金额:%s'%(self.payment,self.amount))
        if float_compare(sum(cost_line.amount for cost_line in self.cost_line_ids),
            sum(line.share_cost for line in self.line_in_ids), precision_digits=decimal_amount.digits) != 0:
            raise UserError(u'采购费用还未分摊或分摊不正确！\n采购费用:%s 分摊总费用:%s'%
                            (sum(cost_line.amount for cost_line in self.cost_line_ids),
                             sum(line.share_cost for line in self.line_in_ids)))
        return

    @api.one
    def _line_qty_write(self):
        if self.order_id:
            line_ids = not self.is_return and self.line_in_ids or self.line_out_ids
            for line in line_ids:
                line.buy_line_id.quantity_in += line.goods_qty

        return

    def _get_invoice_vals(self, partner_id, category_id, date,amount, tax_amount):
        '''返回创建 money_invoice 时所需数据'''
        return {
            'move_id': self.buy_move_id.id,
            'name': self.name,
            'partner_id': partner_id.id,
            'category_id': category_id.id,
            'date': date,
            'amount': amount,
            'reconciled': 0,
            'to_reconcile': amount,
            'tax_amount': tax_amount,
            'date_due': self.date_due,
            'state': 'draft'
        }

    def _receipt_make_invoice(self):
        '''入库单/退货单 生成结算单'''
        invoice_id = False
        if not self.is_return:
            if not self.invoice_by_receipt:
                return False
            amount = self.amount
            tax_amount = sum(line.tax_amount for line in self.line_in_ids)
        else:
            amount = -self.amount
            tax_amount = - sum(line.tax_amount for line in self.line_out_ids)
        categ = self.env.ref('money.core_category_purchase')
        if not float_is_zero(amount,2):
            invoice_id = self.env['money.invoice'].create(
                self._get_invoice_vals(self.partner_id, categ, self.date, amount, tax_amount)
            )
            self.invoice_id = invoice_id.id
        return invoice_id

    @api.one
    def _buy_amount_to_invoice(self):
        '''采购费用产生结算单'''
        if sum(cost_line.amount for cost_line in self.cost_line_ids) > 0:
            for line in self.cost_line_ids:
                if not float_is_zero(line.amount,2):
                    self.env['money.invoice'].create(
                        self._get_invoice_vals(line.partner_id, line.category_id, self.date, line.amount + line.tax, line.tax)
                    )
        return

    def _make_payment(self, invoice_id, amount, this_reconcile):
        '''根据传入的invoice_id生成付款单'''
        categ = self.env.ref('money.core_category_purchase')
        money_lines = [{'bank_id': self.bank_account_id.id, 'amount': this_reconcile}]
        source_lines = [{'name': invoice_id.id,
                         'category_id': categ.id,
                         'date': invoice_id.date,
                         'amount': amount,
                         'reconciled': 0.0,
                         'to_reconcile': amount,
                         'this_reconcile': this_reconcile}]
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
                'state': 'draft'})
        return money_order

    def _create_voucher_line(self, account_id, debit, credit, voucher_id, goods_id):
        '''返回voucher line'''
        voucher = self.env['voucher.line'].create({
            'name': self.name,
            'account_id': account_id and account_id.id,
            'debit': debit,
            'credit': credit,
            'voucher_id': voucher_id and voucher_id.id,
            'goods_id': goods_id and goods_id.id,
        })
        return voucher

    @api.one
    def create_voucher(self):
        '''
        借： 商品分类对应的会计科目 一般是库存商品
        贷：类型为支出的类别对应的会计科目 一般是材料采购

        当一张入库单有多个产品的时候，按对应科目汇总生成多个借方凭证行。

        采购退货单生成的金额为负
        '''
        vouch_id = self.env['voucher'].create({'date': self.date})

        sum_amount = 0
        if not self.is_return:
            for line in self.line_in_ids:
                # 借方明细
                self._create_voucher_line(line.goods_id.category_id.account_id,
                                          line.amount, 0, vouch_id, line.goods_id)
                sum_amount += line.amount

            category_expense = self.env.ref('money.core_category_purchase')
            # 贷方明细
            self._create_voucher_line(category_expense.account_id,
                                      0, sum_amount, vouch_id, False)
        if self.is_return:
            for line in self.line_out_ids:
                # 借方明细
                self._create_voucher_line(line.goods_id.category_id.account_id,
                                          -line.amount, 0, vouch_id, line.goods_id)
                sum_amount += line.amount

            category_expense = self.env.ref('money.core_category_purchase')
            # 贷方明细
            self._create_voucher_line(category_expense.account_id,
                                      0, -sum_amount, vouch_id, False)

        self.voucher_id = vouch_id
        self.voucher_id.voucher_done()
        return vouch_id

    @api.one
    def buy_receipt_done(self):
        '''审核采购入库单/退货单，更新本单的付款状态/退款状态，并生成结算单和付款单'''
        #报错
        self._wrong_receipt_done()
        # 调用wh.move中审核方法，更新审核人和审核状态
        self.buy_move_id.approve_order()

        #将收货/退货数量写入订单行
        self._line_qty_write()

        # 创建入库的会计凭证
        self.create_voucher()

        # 入库单/退货单 生成结算单
        invoice_id = self._receipt_make_invoice()
        # 采购费用产生结算单
        self._buy_amount_to_invoice()
        # 生成付款单
        if self.payment:
            flag = not self.is_return and 1 or -1
            amount = flag * self.amount
            this_reconcile = flag * self.payment
            self._make_payment(invoice_id, amount, this_reconcile)
        # 生成分拆单 FIXME:无法跳转到新生成的分单
        if self.order_id and not self.modifying:
            return self.order_id.buy_generate_receipt()

    @api.one
    def buy_receipt_draft(self):
        '''反审核采购入库单/退货单，更新本单的付款状态/退款状态，并删除生成的结算单、付款单及凭证'''
        # 查找产生的付款单
        source_line = self.env['source.order.line'].search(
                [('name', '=', self.invoice_id.id)])
        for line in source_line:
            line.money_id.money_order_draft()
            line.money_id.unlink()
        # 查找产生的结算单
        invoice_ids = self.env['money.invoice'].search(
                [('name', '=', self.invoice_id.name)])
        invoice_ids.money_invoice_draft()
        invoice_ids.unlink()
        # 如果存在分单，则将差错修改中置为 True，再次审核时不生成分单
        self.modifying = False
        receipt_ids = self.search(
            [('order_id', '=', self.order_id.id)])
        if len(receipt_ids) > 1:
            self.modifying = True
        # 修改订单行中已执行数量
        if self.order_id:
            line_ids = not self.is_return and self.line_in_ids or self.line_out_ids
            for line in line_ids:
                line.buy_line_id.quantity_in -= line.goods_qty
        # 调用wh.move中反审核方法，更新审核人和审核状态
        self.buy_move_id.cancel_approved_order()

        # 反审核采购入库单时删除对应的入库凭证
        if self.voucher_id:
            if self.voucher_id.state == 'done':
                self.voucher_id.voucher_draft()
            self.voucher_id.unlink()

    @api.one
    def buy_share_cost(self):
        '''入库单上的采购费用分摊到入库单明细行上'''
        total_amount = 0
        for line in self.line_in_ids:
            total_amount += line.amount
        cost = sum(cost_line.amount for cost_line in self.cost_line_ids)
        for line in self.line_in_ids:
            line.share_cost = cost / total_amount * line.amount
        return True


class wh_move_line(models.Model):
    _inherit = 'wh.move.line'
    _description = u"采购入库明细"

    buy_line_id = fields.Many2one('buy.order.line',
                                  u'购货单行', ondelete='cascade',
                                  help=u'对应的购货订单行')
    share_cost = fields.Float(u'采购费用',
                              digits=dp.get_precision('Amount'),
                              help=u'点击分摊按钮或审核时将采购费用进行分摊得出的费用')

    def _buy_get_price_and_tax(self):
        self.tax_rate = self.env.user.company_id.import_tax_rate
        self.price_taxed = self.goods_id.cost

    @api.multi
    @api.onchange('goods_id', 'tax_rate')
    def onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的成本价，以及公司的进项税'''
        self.ensure_one()
        if self.goods_id:
            if not self.goods_id.cost:
                raise UserError(u'请先设置商品的成本！')

            is_return = self.env.context.get('default_is_return')
            # 如果是采购入库单行 或 采购退货单行
            if (self.type == 'in' and not is_return) or (self.type == 'out' and is_return):
                self._buy_get_price_and_tax()

        return super(wh_move_line,self).onchange_goods_id()
