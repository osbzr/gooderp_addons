# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
import datetime


class test_pos_order(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(test_pos_order, self).setUp()
        self.pos_config = self.env.ref('gooderp_pos.pos_config_sell')
        self.session = self.env['pos.session'].create({
            'config_id': self.pos_config.id,
        })

    def test_data_handling(self):
        '''在会话中结账后生成pos order'''
        order_data = {
            'pos_session_id': self.session.id,
            'partner_id': self.env.ref('core.yixun').id,
            'creation_date': datetime.datetime.now(),
            'lines': [(0, 0, {
                'product_id': self.env.ref('goods.mouse').id,
                'qty': 1,
                'price_unit': 100,
                'discount': 0,
            })],
            'statement_ids': [(0, 0, {
                'statement_id': self.env.ref('core.alipay').id,
                'amount': 100,
                'name': datetime.datetime.now(),
            })]
        }
        self.env['pos.order'].data_handling(order_data)

        # create_from_ui(orders)方法测试
        # 入库mouse,以便发货单审核通过
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        orders = [{'data': order_data}]
        self.env['pos.order'].create_from_ui(orders)
