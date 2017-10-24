# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
import datetime


class TestPosOrder(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(TestPosOrder, self).setUp()
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
        pos_order_data = self.env['pos.order'].data_handling(order_data)

        # create_from_ui(orders)方法测试
        orders = [{'data': order_data}]
        with self.assertRaises(UserError):  # 缺货时报错：发货单不能完成审核
            self.env['pos.order'].create_from_ui(orders)
        # 入库mouse,以便发货单审核通过
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        pos_order_id = self.env['pos.order'].create_from_ui(orders)
        pos_order = self.env['pos.order'].browse(pos_order_id)
        self.assertEqual(pos_order.state, 'paid')

        # 创建另一个pos order，更新会话的付款明细行中金额
        orders = [{'data': order_data}]
        self.env['pos.order'].create_from_ui(orders)

    def test_action_pos_order_paid(self):
        '''在会话中结账后生成pos order,该单还没付清'''
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
                'amount': 50,
                'name': datetime.datetime.now(),
            })]
        }
        pos_order_data = self.env['pos.order'].data_handling(order_data)

        # create_from_ui(orders)方法测试
        # 入库mouse,以便发货单审核通过
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        pos_order = self.env['pos.order'].create(pos_order_data)
        with self.assertRaises(UserError):  # 报错：该单还没付清
            pos_order.action_pos_order_paid()

    def test_pos_order_line_negative_qty(self):
        '''在会话中结账后生成pos order,退货的情况'''
        order_data = {
            'pos_session_id': self.session.id,
            'partner_id': self.env.ref('core.yixun').id,
            'creation_date': datetime.datetime.now(),
            'lines': [(0, 0, {
                'product_id': self.env.ref('goods.mouse').id,
                'qty': -1,
                'price_unit': 100,
                'discount': 0,
            })],
            'statement_ids': [(0, 0, {
                'statement_id': self.env.ref('core.alipay').id,
                'amount': -100,
                'name': datetime.datetime.now(),
            })]
        }
        orders = [{'data': order_data}]
        self.env['pos.order'].create_from_ui(orders)
