# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestExpressMenu(TransactionCase):

    def setUp(self):
        ''' 准备基本数据 '''
        super(TestExpressMenu, self).setUp()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])

    def test_get_moves_html(self):
        ''' 测试 get_moves_html '''
        move = self.delivery.sell_move_id
#         self.env['wh.move'].get_moves_html(move.id)

        with self.assertRaises(UserError):
            self.env['wh.move'].get_moves_html(move.id)

        # 承运商暂不支持 或者承运商商户简称输入错误
        with self.assertRaises(UserError):
            self.delivery.express_type = 'SF_test'
            self.env['wh.move'].get_moves_html(move.id)

#         self.delivery.express_type = 'YTO'
#         self.env['wh.move'].get_moves_html(move.id)

    def test_get_moves_html_package(self):
        ''' 测试 get_moves_html_package '''
        move = self.delivery.sell_move_id
        self.env['wh.move'].get_moves_html_package(move.id)
