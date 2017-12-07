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
