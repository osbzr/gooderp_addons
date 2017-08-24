# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo.tools import float_compare
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
            order.amount_paid = order.amount_return = 0.0
            order.amount_paid = sum(payment.amount for payment in order.payment_line_ids)
            order.amount_total = sum(line.subtotal for line in order.line_ids)

    def data_handling(self, order_data):
        line_data_list = [[0, 0, {'goods_id': line[2].get('product_id'),
                                  'qty': line[2].get('qty'),
                                  'price': line[2].get('price_unit'),
                                  'discount_amount': line[2].get('discount')*\
                                                     line[2].get('price_unit') * line[2].get('qty')/100,
                                  'discount_rate': line[2].get('discount'),
                                  'subtotal': line[2].get('price_unit') * line[2].get('qty') - \
                                              line[2].get('discount') * line[2].get('price_unit') * line[2].get('qty')/100
                                  }]
                          for line in order_data.get('lines')]
        payment_line_list = [[0, 0, {
            'bank_account_id': line[2].get('statement_id'),
            'amount': line[2].get('amount'),
            'pay_date': line[2].get('name'),
            'session_id': order_data.get('pos_session_id'),
        }]for line in order_data.get('statement_ids')]
        sell_order_data = dict(
            session_id=order_data.get('pos_session_id'),
            partner_id=order_data.get('partner_id') or self.env.ref('gooderp_pos.pos_partner').id,
            user_id=order_data.get('user_id') or 1,
            line_ids=line_data_list,
            date=order_data.get('creation_date'),
            warehouse_id=self.env.ref('core.warehouse_general').id,
            warehouse_dest_id=self.env.ref('warehouse.warehouse_customer').id,
            payment_line_ids=payment_line_list,
        )
        return sell_order_data

    @api.model
    def create_from_ui(self, orders):
        order_ids = []
        for order in orders:
            order_data = order.get('data')
            sell_order_data = self.data_handling(order_data)
            pos_order = self.create(sell_order_data)
            # pos_order.sell_delivery_done()
            order_ids.append(pos_order.id)

            prec_acc = self.env['decimal.precision'].precision_get('Account')
            for payments in order_data.get('statement_ids'):
                if not float_is_zero(payments[2].get('amount'), precision_digits=prec_acc):
                    pos_order.add_payment(self._payment_fields(payments[2]))
            try:
                pos_order.action_pos_order_paid()
            except psycopg2.OperationalError:
                # do not hide transactional errors, the order(s) won't be saved!
                raise
            except Exception as e:
                _logger.error(u'不能完整地处理POS 订单: %s', tools.ustr(e))

            # fixme:生成sell_delivery
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
                need_create = False
                break
        if need_create:
            self.env['payment.line'].with_context(context).create(args)

        return True

    @api.multi
    def action_pos_order_paid(self):
        decimal = self.env.ref('core.decimal_amount')
        for order in self:
            if (not order.line_ids) or (not order.payment_line_ids) or \
                            float_compare(order.amount_total, order.amount_paid, decimal.digits) == 1:
                raise UserError(u"该单还没付清")
            order.write({'state': 'paid'})


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

    order_id = fields.Many2one('pos.order', string=u'订单号', ondelete='cascade')
    bank_account_id = fields.Many2one('bank.account', u'付款方式')
    amount = fields.Float(u'金额')
    pay_date = fields.Datetime(u'付款时间')


class SellDelivery(models.Model):
    _inherit = "sell.delivery"
    """
    POS 和 gooderp结合 订单部分的主要内容.
    """
    #TODO:估计还有很多字段上的关联要添加,这个还得进一步的测试.

    session_id = fields.Many2one(
        'pos.session', string=u'会话', index=True,
        readonly=True)
    config_id = fields.Many2one('pos.config', related='session_id.config_id', string=u"POS")

    def data_handling(self, order_data):
        line_data_list = [[0, 0, {'goods_id': line[2].get('product_id'),
                                  'goods_qty': line[2].get('qty'),
                                  'price_taxed': line[2].get('price_unit'),
                                  'discount_amount': line[2].get('discount')*\
                                                     line[2].get('price_unit') * line[2].get('qty')/100,
                                  'discount_rate': line[2].get('discount'),
                                  'type': 'out',
                                  }]
                          for line in order_data.get('lines')]
        sell_order_data = dict(
            session_id=order_data.get('pos_session_id'),
            partner_id=order_data.get('partner_id') or self.env.ref('gooderp_pos.pos_partner').id,
            user_id=order_data.get('user_id') or 1,
            line_out_ids=line_data_list,
            date=order_data.get('creation_date'),
            warehouse_id=self.env.ref('core.warehouse_general').id,
            warehouse_dest_id=self.env.ref('warehouse.warehouse_customer').id,
            note=u"POS订单",
            date_due=order_data.get('creation_date'),
            bank_account_id=self.env.ref('gooderp_pos.pos_bank_account_cash').id,
        )
        return sell_order_data
