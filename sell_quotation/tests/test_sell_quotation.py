# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSellQuotation(TransactionCase):
    def setUp(self):
        super(TestSellQuotation, self).setUp()
        self.sell_quotation = self.env.ref('sell_quotation.sell_quotation_1')
        self.sell_quotation_line = self.env.ref('sell_quotation.sell_quotation_line_1')
        self.partner_id = self.env.ref('core.jd')
        self.province_id = self.env['country.state'].search(
            [('name', '=', u'河北省')])
        self.city_id = self.env['all.city'].search(
            [('city_name', '=', u'石家庄市')])
        self.county_id = self.env['all.county'].search(
            [('county_name', '=', u'正定县')])

        self.goods_mouse = self.env.ref('goods.mouse')  # goods  mouse

    def test_sell_quotation_done(self):
        ''' 测试 审核报价单 方法'''
        self.sell_quotation.sell_quotation_done()
        # 重复审核 报错
        with self.assertRaises(UserError):
            self.sell_quotation.sell_quotation_done()
        # 没有明细行 报错
        sell_quotation_2 = self.env.ref('sell_quotation.sell_quotation_2')
        with self.assertRaises(UserError):
            sell_quotation_2.sell_quotation_done()

    def test_sell_quotation_draft(self):
        ''' 测试 反审核报价单 方法'''
        self.sell_quotation.sell_quotation_done()
        self.sell_quotation.sell_quotation_draft()
        # 重复反审核 报错
        with self.assertRaises(UserError):
            self.sell_quotation.sell_quotation_draft()

    def test_onchange_partner_id(self):
        ''' 选择客户带出其默认地址信息 '''
        self.sell_quotation.onchange_partner_id()

        # partner 不存在默认联系人
        self.partner_id.write({'child_ids':
                               [(0, 0, {'contact': u'小东',
                                        'province_id': self.province_id.id,
                                        'city_id': self.city_id.id,
                                        'county_id': self.county_id.id,
                                        'town': u'曹路镇',
                                        'detail_address': u'金海路1688号',
                                        }
                                 )]})
        self.sell_quotation.onchange_partner_id()
        # partner 存在默认联系人
        for child in self.partner_id.child_ids:
            child.mobile = '1385559999'
            child.phone = '55558888'
            child.qq = '11116666'
            child.is_default_add = True
        self.sell_quotation.onchange_partner_id()

    def test_onchange_partner_address_id(self):
        ''' sell.quotation onchange partner address id '''
        address = self.env['partner.address'].create({'contact': u'小东',
                                                      'province_id': self.province_id.id,
                                                      'city_id': self.city_id.id,
                                                      'county_id': self.county_id.id,
                                                      'town': u'曹路镇',
                                                      'detail_address': u'金海路1688号',
                                                      })
        self.sell_quotation.partner_address_id = address.id
        self.sell_quotation.onchange_partner_address_id()


class TestSellQuotationLine(TransactionCase):
    def setUp(self):
        super(TestSellQuotationLine, self).setUp()
        self.sell_quotation_line = self.env.ref('sell_quotation.sell_quotation_line_1')

    def test_onchange_goods_id(self):
        ''' 当报价单行的商品变化时，带出商品上的计量单位、含税价 '''
        goods = self.env.ref('goods.keyboard')
        self.sell_quotation_line.goods_id = goods.id
        self.sell_quotation_line.onchange_goods_id()


class TestSellOrderLine(TransactionCase):
    def setUp(self):
        super(TestSellOrderLine, self).setUp()
        self.sell_line = self.env.ref('sell.sell_order_line_1')
        self.sell_quotation = self.env.ref('sell_quotation.sell_quotation_1')

    def test_onchange_quantity(self):
        ''' 当销货订单行的商品变化时，带出报价单 '''
        self.sell_line.quantity = 80
        # 报价单不存在，报错
        with self.assertRaises(UserError):
            self.sell_line.onchange_quantity()

        # 报价单存在
        self.sell_quotation.sell_quotation_done()
        self.sell_line.onchange_quantity()
