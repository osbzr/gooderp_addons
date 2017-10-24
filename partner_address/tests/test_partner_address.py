# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from psycopg2 import IntegrityError


class TestPartnerAddress(TransactionCase):
    '''测试业务伙伴的联系人地址'''

    def setUp(self):
        '''准备数据'''
        super(TestPartnerAddress, self).setUp()
        self.partner_id = self.env.ref('core.jd')
        self.partner = self.env['partner'].search(
            [('id', '=', self.partner_id.id)])
        self.partner.write({'child_ids':
                            [(0, 0,
                              {'contact': u'小东',
                               'mobile': '1385559999',
                               }
                              )]
                            })

    def test_onchange_province(self):
        '''测试onchange province'''
        # 不存在省
        for child in self.partner.child_ids:
            child.onchange_province()
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        # 存在省不存在市
        for child in self.partner.child_ids:
            child.province_id = province.id
            child.city_id = False
            child.onchange_province()
        # 存在省存在市，但市不属于省
        city = self.env['all.city'].search([('city_name', '=', u'上海市')])
        for child in self.partner.child_ids:
            child.city_id = city.id
            child.onchange_province()
        # 存在省存在市，市属于省
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        for child in self.partner.child_ids:
            child.city_id = city.id
            child.onchange_province()
        # 存在省存在市存在县，但县不属于市
        county = self.env['all.county'].search([('county_name', '=', u'太康县')])
        for child in self.partner.child_ids:
            child.county_id = county.id
            child.onchange_province()
        # 存在省存在市存在县，县属于市
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        for child in self.partner.child_ids:
            child.county_id = county.id
            child.onchange_province()

    def test_onchange_city(self):
        '''测试onchange city'''
        # 不存在市
        for child in self.partner.child_ids:
            child.onchange_city()
        # 存在市不存在省
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        for child in self.partner.child_ids:
            child.city_id = city.id
            child.onchange_city()
        # 存在市不存在省，不存在县
        for child in self.partner.child_ids:
            child.province_id = False
            child.county_id = False
            child.city = city.id
            child.onchange_city()
        # 存在市存在省存在县，但县不属于市
        county = self.env['all.county'].search(
            [('county_name', '=', u'承德县')])
        for child in self.partner.child_ids:
            child.province_id = False
            child.county_id = county.id
            child.onchange_city()
        # 存在市不存在省，存在县，县属于市
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        for child in self.partner.child_ids:
            child.province_id = False
            child.county_id = county.id
            child.city_id = city.id
            child.onchange_city()
        # 存在市存在省
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        for child in self.partner.child_ids:
            child.province_id = province.id
            child.onchange_city()
        # 存在市存在省存在县，县属于市
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        for child in self.partner.child_ids:
            child.county_id = county.id
            child.onchange_city()
        # 存在市存在省存在县，县属于市，但省与  市所在的省相同
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        for child in self.partner.child_ids:
            child.city_id = city.id
            child.province_id = province.id
            child.county_id = county.id
            child.onchange_city()
        # 存在市存在省存在县，县属于市，但省与  市所在的省不同
        province = self.env['country.state'].search([('name', '=', u'四川省')])
        for child in self.partner.child_ids:
            child.province_id = province.id
            child.onchange_city()
        # 存在市存在省存在县，但县不属于市
        county = self.env['all.county'].search([('county_name', '=', u'承德县')])
        for child in self.partner.child_ids:
            child.county_id = county.id
            child.province_id = province.id
            child.onchange_city()
        # 存在市存在省存在县，县不属于市，省与  市所在的省不同
        province = self.env['country.state'].search([('name', '=', u'四川省')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        county = self.env['all.county'].search([('county_name', '=', u'承德县')])
        for child in self.partner.child_ids:
            child.province_id = province.id
            child.city_id = city.id
            child.county_id = county.id
            child.onchange_city()
        # 存在市存在省存在县，县不属于市，但省与  市所在的省相同
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        county = self.env['all.county'].search([('county_name', '=', u'承德县')])
        self.partner.province_id = province.id
        for child in self.partner.child_ids:
            child.province_id = province.id
            child.city_id = city.id
            child.county_id = county.id
            child.onchange_city()
        # 存在市存在省不存在县，省与  市所在的省不同
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        province = self.env['country.state'].search([('name', '=', u'山西省')])
        for child in self.partner.child_ids:
            child.province_id = province.id
            child.city_id = city.id
            child.county_id = False
            child.onchange_city()
        # 存在市存在省不存在县，省与  市所在的省相同
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        for child in self.partner.child_ids:
            child.province_id = province.id
            child.city_id = city.id
            child.county_id = False
            child.onchange_city()

    def test_onchange_county(self):
        '''测试onchange county'''
        county = self.env['all.county'].search([('county_name', '=', u'正定县')])
        for child in self.partner.child_ids:
            child.county_id = county.id
            child.onchange_county()


class TestPartner(TransactionCase):

    def setUp(self):
        '''准备数据'''
        super(TestPartner, self).setUp()
        self.partner_id = self.env.ref('core.jd')
        self.province_id = self.env['country.state'].search(
            [('name', '=', u'河北省')])
        self.city_id = self.env['all.city'].search(
            [('city_name', '=', u'石家庄市')])
        self.county_id = self.env['all.county'].search(
            [('county_name', '=', u'正定县')])

    def test_compute_partner_address(self):
        '''测试如果业务伙伴地址中有默认地址，则显示在业务伙伴列表上'''
        partner = self.env['partner'].search(
            [('id', '=', self.partner_id.id)])
        # 没有联系人地址child_ids时
        partner._compute_partner_address()
        # 有联系人地址child_ids，并为默认地址时
        partner.write({'child_ids':
                       [(0, 0,
                         {'contact': u'小东',
                          'province_id': self.province_id.id,
                          'city_id': self.city_id.id,
                          'county_id': self.county_id.id,
                          'town': u'曹路镇',
                          'detail_address': u'金海路1688号',
                          }
                         )]
                       })
        partner._compute_partner_address()
        for child in partner.child_ids:
            child.mobile = '1385559999'
            child.phone = '55558888'
            child.qq = '11116666'
            child.is_default_add = True

        partner._compute_partner_address()
        self.assertEqual(partner.contact, u'小东')
        self.assertEqual(partner.mobile, u'1385559999')
        self.assertEqual(partner.phone, u'55558888')
        self.assertEqual(partner.qq, u'11116666')
        addr = ''
        for child in partner.child_ids:
            addr = '%s%s%s%s%s' % (child.province_id.name,
                                   child.city_id.city_name,
                                   child.county_id.county_name,
                                   child.town,
                                   child.detail_address)
        self.assertEqual(partner.address, addr)

    def test_name_get(self):
        address = self.env['partner.address'].create({'contact': u'小东',
                                                      'province_id': self.province_id.id,
                                                      'city_id': self.city_id.id,
                                                      'county_id': self.county_id.id,
                                                      'town': u'曹路镇',
                                                      'detail_address': u'金海路1688号',
                                                      })
        name = address.name_get()
        real_name = '%s%s%s%s%s' % (address.province_id and address.province_id.name or '',
                                    address.city_id and address.city_id.city_name or '',
                                    address.county_id and address.county_id.county_name or '',
                                    address.town or '',
                                    address.detail_address or '')
        self.assertTrue(name[0][1] == real_name)
