# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo.tools import float_compare
import math
from datetime import timedelta
from functools import partial

import psycopg2

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo.http import request
import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _name = "pos.order"
    _description = u"POS订单"
    _order = "id desc"

    def _default_session(self):
        return self.env['pos.session'].search([
            ('state', '=', 'opened'),
            ('user_id', '=', self.env.uid)], limit=1)

    name = fields.Char(
        string=u'订单编号',
        required=True,
        readonly=True,
        copy=False,
        default='/'
    )
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        required=True,
        readonly=True,
        default=lambda self: self.env['res.company']._company_default_get()
    )
    date = fields.Datetime(
        string=u'单据日期',
        readonly=True,
        index=True,
        default=fields.Datetime.now
    )
    user_id = fields.Many2one(
        'res.users',
        string=u'销售员',
        help="Person who uses the cash register. It can be a reliever, a student or an interim employee.",
        default=lambda self: self.env.uid
    )
    amount_total = fields.Float(
        compute='_compute_amount_all',
        string=u'总金额',
        digits=dp.get_precision('Amount'),
    )
    amount_paid = fields.Float(
        compute='_compute_amount_all',
        string=u'已支付',
        states={'draft': [('readonly', False)]}, readonly=True, digits=dp.get_precision('Amount'),
    )
    # amount_return = fields.Float(
    #     compute='_compute_amount_all',
    #     string=u'退款',
    #     digits=dp.get_precision('Amount'),
    # )
    line_ids = fields.One2many(
        'pos.order.line',
        'order_id',
        string=u'订单明细',
        states={'draft': [('readonly', False)]},
        readonly=True,
        copy=True
    )
    payment_line_ids = fields.One2many(
        'pos.payment.line',
        'order_id',
        u'付款方式',
        states={'draft': [('readonly', False)]},
        readonly=True
    )
    partner_id = fields.Many2one(
        'partner',
        string=u'客户',
        index=True,
        states={'draft': [('readonly', False)], 'paid': [('readonly', False)]}
    )
    sequence_number = fields.Integer(
        string='Sequence Number',
        help='A session-unique sequence number for the order',
        default=1
    )
    session_id = fields.Many2one(
        'pos.session',
        string=u'会话',
        required=True,
        index=True,
        domain="[('state', '=', 'opened')]",
        states={'draft': [('readonly', False)]},
        readonly=True,
        default=_default_session
    )
    config_id = fields.Many2one(
        'pos.config',
        related='session_id.config_id',
        string=u"POS"
    )
    warehouse_id = fields.Many2one(
        'warehouse',
        related='session_id.config_id.warehouse_id',
        string=u'调出仓库',
        store=True
    )
    state = fields.Selection(
        [('draft', u'新建'),
         ('paid', u'已付款'),
         ],
        u'状态',
        readonly=True,
        copy=False,
        default='draft')
    note = fields.Text(u'备注')

    @api.depends('payment_line_ids', 'line_ids.subtotal')
    def _compute_amount_all(self):
        for order in self:
            order.amount_paid = 0.0
            order.amount_paid = sum(
                payment.amount for payment in order.payment_line_ids)
            order.amount_total = sum(line.subtotal for line in order.line_ids)

    def data_handling(self, order_data):
        """准备创建 pos order 需要的数据"""
        payment_line_list = []
        line_data_list = [[0, 0, {'goods_id': line[2].get('product_id'),
                                  'qty': line[2].get('qty'),
                                  'price': line[2].get('price_unit'),
                                  'discount_amount': line[2].get('discount') *
                                  line[2].get('price_unit') *
                                  line[2].get('qty') / 100,
                                  'discount_rate': line[2].get('discount'),
                                  'subtotal': line[2].get('price_unit') * line[2].get('qty') -
                                  line[2].get(
                                      'discount') * line[2].get('price_unit') * line[2].get('qty') / 100
                                  }]
                          for line in order_data.get('lines')]
        prec_amt = self.env['decimal.precision'].precision_get('Amount')
        # 付款金额为0时不生成付款明细
        for line in order_data.get('statement_ids'):
            if not float_is_zero(line[2].get('amount'), precision_digits=prec_amt):
                payment_line_list.append((0, 0, {
                    'bank_account_id': line[2].get('statement_id'),
                    'amount': line[2].get('amount'),
                    'pay_date': line[2].get('name'),
                }))
        pos_order_data = dict(
            session_id=order_data.get('pos_session_id'),
            partner_id=order_data.get('partner_id') or self.env.ref(
                'gooderp_pos.pos_partner').id,
            user_id=order_data.get('user_id') or 1,
            line_ids=line_data_list,
            date=order_data.get('creation_date'),
            payment_line_ids=payment_line_list,
        )
        return pos_order_data

    @api.model
    def create_from_ui(self, orders):
        """在会话中结账后生成pos order，并由pos order生成相应的发货单/退货单及收款单 """
        order_ids = []
        for order in orders:
            order_data = order.get('data')
            pos_order_data = self.data_handling(order_data)
            pos_order = self.create(pos_order_data)
            order_ids.append(pos_order.id)

            prec_amt = self.env['decimal.precision'].precision_get('Amount')
            for payments in order_data.get('statement_ids'):
                if not float_is_zero(payments[2].get('amount'), precision_digits=prec_amt):
                    pos_order.add_payment(self._payment_fields(payments[2]))
            try:
                pos_order.action_pos_order_paid()
            except psycopg2.OperationalError:
                # do not hide transactional errors, the order(s) won't be saved!
                raise
            except Exception as e:
                _logger.error(u'不能完整地处理POS 订单: %s', tools.ustr(e))

            # 生成sell_delivery，并审核
            records = pos_order.create_sell_delivery()
            invoice_ids = [record.invoice_id for record in records]
            # 生成收款单，并审核
            pos_order.create_money_order(
                invoice_ids, pos_order.payment_line_ids)
        return order_ids

    def _payment_fields(self, ui_paymentline):
        return {
            'amount':       ui_paymentline['amount'] or 0.0,
            'payment_date': ui_paymentline['name'],
            'statement_id': ui_paymentline['statement_id'],
            'payment_name': ui_paymentline.get('note', False),
        }

    def add_payment(self, data):
        """Create a new payment for the order"""
        args = {
            'amount': data['amount'],
            'pay_date': data.get('payment_date', fields.Date.today()),
        }

        statement_id = data.get('statement_id', False)
        assert statement_id, "No statement_id passed to the method!"

        context = dict(self.env.context)
        context.pop('pos_session_id', False)
        bank_account = self.env['bank.account'].browse(statement_id)
        args.update({
            'session_id': self.session_id.id,
            'bank_account_id': bank_account.id,
        })
        need_create = True  # 是否需要创建付款明细行
        for line in self.session_id.payment_line_ids:
            if line.bank_account_id.id == statement_id:
                line.amount += data['amount']
                line.pay_date = args['pay_date']
                need_create = False
                break
        if need_create:
            self.env['payment.line'].with_context(context).create(args)

        return True

    @api.multi
    def action_pos_order_paid(self):
        decimal = self.env.ref('core.decimal_amount')
        for order in self:
            if float_compare(order.amount_total, order.amount_paid, decimal.digits) == 1:
                raise UserError(u"该单还没付清")
            order.write({'state': 'paid'})

    @api.multi
    def create_sell_delivery(self):
        """由pos订单生成销售发货单"""
        for order in self:
            records = []
            delivery_line = []  # 销售发货单行
            return_line = []  # 销售退货单行
            for line in order.line_ids:
                if line.qty < 0:
                    return_line.append(order._get_delivery_line(line))
                else:
                    delivery_line.append(order._get_delivery_line(line))
            if delivery_line:
                sell_delivery = order._generate_delivery(
                    delivery_line, is_return=False)
                sell_delivery.sell_delivery_done()
                if sell_delivery.state != 'done':   # fixme:缺货时如何处理
                    raise UserError(u'发货单不能完成审核')
                records.append(sell_delivery)
            if return_line:
                sell_return = order._generate_delivery(
                    return_line, is_return=True)
                sell_return.sell_delivery_done()
                if sell_return.state != 'done':
                    raise UserError(u'退货单不能完成审核')
                records.append(sell_return)
            return records

    @api.one
    def _get_delivery_line(self, line):
        '''返回销售发货/退货单行'''
        return {
            'type': line.qty > 0 and 'out' or 'in',
            'goods_id': line.goods_id.id,
            'uos_id': line.goods_id.uos_id.id,
            'goods_qty': math.fabs(line.qty),
            'uom_id': line.goods_id.uom_id.id,
            'cost_unit': line.goods_id.cost,
            'price_taxed': line.price,
            'discount_rate': line.discount_rate,
            'discount_amount': line.discount_amount,
        }

    def _generate_delivery(self, delivery_line, is_return):
        '''根据明细行生成发货单或退货单'''
        # 如果退货，warehouse_dest_id，warehouse_id要调换
        warehouse = (not is_return
                     and self.warehouse_id
                     or self.env.ref("warehouse.warehouse_customer"))
        warehouse_dest = (not is_return
                          and self.env.ref("warehouse.warehouse_customer")
                          or self.warehouse_id)
        rec = (not is_return and self.with_context(is_return=False)
               or self.with_context(is_return=True))
        delivery_id = rec.env['sell.delivery'].create({
            'partner_id': self.partner_id.id,
            'warehouse_id': warehouse.id,
            'warehouse_dest_id': warehouse_dest.id,
            'user_id': self.user_id.id,
            'date': self.date,
            'date_due': self.date,
            'pos_order_id': self.id,
            'origin': 'sell.delivery',
            'is_return': is_return,
            'note': self.note,
        })
        if not is_return:
            delivery_id.write({'line_out_ids': [
                (0, 0, line[0]) for line in delivery_line]})
        else:
            delivery_id.write({'line_in_ids': [
                (0, 0, line[0]) for line in delivery_line]})
        return delivery_id

    def create_money_order(self, invoice_ids, payment_line_ids):
        '''生成收款单'''
        categ = self.env.ref('money.core_category_sale')
        money_lines = []    # 收款明细行
        source_lines = []   # 待核销行
        for line in payment_line_ids:
            money_lines.append({
                'bank_id': line.bank_account_id.id,
                'amount': line.amount,
            })
        for invoice_id in invoice_ids:
            source_lines.append({
                'name': invoice_id and invoice_id.id,
                'category_id': categ.id,
                'date': invoice_id and invoice_id.date,
                'amount': invoice_id.amount,
                'reconciled': 0.0,
                'to_reconcile': invoice_id.amount,
                'this_reconcile': invoice_id.amount,
            })
        rec = self.with_context(type='get')
        money_order = rec.env['money.order'].create({
            'partner_id': self.partner_id.id,
            'date': self.date[:10],
            'line_ids': [(0, 0, line) for line in money_lines],
            'source_ids': [(0, 0, line) for line in source_lines],
            'amount': self.amount_total,
            'reconciled': self.amount_total,
            'to_reconcile': self.amount_total,
            'state': 'draft',
            'origin_name': self.name,
            'note': self.note or '',
        })
        money_order.money_order_done()
        return money_order


class PosOrderLine(models.Model):
    _name = "pos.order.line"
    _description = u"POS订单明细"

    order_id = fields.Many2one(
        'pos.order',
        string=u'订单号',
        ondelete='cascade'
    )
    goods_id = fields.Many2one(
        'goods',
        string=u'商品',
        required=True,
    )
    price = fields.Float(
        u'单价',
        digits=dp.get_precision('Price'),
    )
    qty = fields.Float(
        u'数量',
        digits=dp.get_precision('Quantity'),
        default=1,
    )
    discount_rate = fields.Float(
        u'折扣率%',
        help=u'折扣率')
    discount_amount = fields.Float(
        u'折扣额',
        help=u'输入折扣率后自动计算得出，也可手动输入折扣额')
    subtotal = fields.Float(
        u'小计',
        compute='_compute_line_all',
        digits=dp.get_precision('Amount'),
    )

    @api.depends('price', 'qty')
    def _compute_line_all(self):
        for line in self:
            line.subtotal = line.price * line.qty - line.discount_amount


class PosPaymentLine(models.Model):
    _name = 'pos.payment.line'
    _description = u"POS订单付款明细"

    order_id = fields.Many2one('pos.order', string=u'订单号', ondelete='cascade')
    bank_account_id = fields.Many2one('bank.account', u'付款方式')
    amount = fields.Float(u'金额')
    pay_date = fields.Datetime(u'付款时间')


class SellDelivery(models.Model):
    _inherit = "sell.delivery"
    """
    POS 和 gooderp结合 订单部分的主要内容.
    """
    # TODO:估计还有很多字段上的关联要添加,这个还得进一步的测试.

    pos_order_id = fields.Many2one(
        'pos.order',
        string=u'POS订单号',
        ondelete='restrict',
        readonly=True,
    )
