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
        self.wave_wizard = self.env['create.wave'].with_context({
            'active_ids': self.delivery.id}).create({
                'active_model': 'sell.delivery',
            })

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

        self.delivery.express_type = 'YTO'
        self.delivery.express_code = '66668888'
        self.env['wh.move'].get_moves_html(move.id)

    def test_get_moves_html_package(self):
        ''' 测试 get_moves_html_package '''
        move = self.delivery.sell_move_id
        self.env['wh.move'].get_moves_html_package(move.id)

    def test_receiver_detail_address(self):
        ''' Test: receiver detail address  '''
        partner = self.env.ref('core.jd')
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        county = self.env['all.county'].search([('county_name', '=', u'正定县')])

        # 有联系人地址child_ids
        partner.write({'child_ids': [(0, 0, {'contact': u'开阖',
                                             'mobile': '123',
                                             'province_id': province.id,
                                             'city_id': city.id,
                                             'county_id': county.id,
                                             'town': u'曹路镇',
                                             'detail_address': u'河北省石家庄市正定县曹路镇金海路1688号',
                                            })]
                       })
        partner._compute_partner_address()

        self.order.sell_order_draft()
        self.order.onchange_partner_id()
        self.order.sell_order_done()
        delivery = self.env['sell.delivery'].search([('order_id', '=', self.order.id)])
        delivery.sell_move_id.get_receiver_goods_message()

        self.order.sell_order_draft()
        partner.child_ids[0].detail_address = '上海市浦东新区曹路镇金海路2588'
        self.order.onchange_partner_id()
        self.order.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search([('order_id', '=', self.order.id)])
        delivery_1.sell_move_id.get_receiver_goods_message()

        self.order.sell_order_draft()
        partner.child_ids[0].detail_address = '内蒙古自治区阿拉善盟阿拉善左旗巴彦浩特镇阿盟一中'
        self.order.onchange_partner_id()
        self.order.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search([('order_id', '=', self.order.id)])
        delivery_1.sell_move_id.get_receiver_goods_message()
