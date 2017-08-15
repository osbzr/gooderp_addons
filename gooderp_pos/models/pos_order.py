# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from functools import partial

import psycopg2

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo.http import request
import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


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

    @api.model
    def create_from_ui(self, orders):
        order_ids = []
        for order in orders:
            order_data = order.get('data')
            sell_order_data = self.data_handling(order_data)
            sell_order_row = self.create(sell_order_data)
            sell_order_row.sell_delivery_done()
            order_ids.append(sell_order_row.id)
        return order_ids

