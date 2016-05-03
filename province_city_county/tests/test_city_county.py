# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase
from psycopg2 import IntegrityError


class test_city_county(TransactionCase):
    '''测试省市县'''

    def setUp(self):
        '''准备数据'''
        super(test_city_county, self).setUp()
        self.partner_id = self.env.ref('core.jd')
        self.partner =  self.env['partner'].search(
                    [('id', '=', self.partner_id.id)])
        for child in self.partner.child_ids:
            child.address_id.detail_address = u'金海路1688号'

    def test_onchange_province(self):
        '''测试onchange province'''
        # 不存在省
        for child in self.partner.child_ids:
            child.address_id.onchange_province()
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        # 存在省不存在市
        for child in self.partner.child_ids:
            child.address_id.province_id = province.id
            child.address_id.onchange_province()
        # 存在省存在市，但市不属于省
        city = self.env['all.city'].search([('city_name', '=', u'上海市')])
        for child in self.partner.child_ids:
            child.address_id.city_id = city.id
            child.address_id.city_id.onchange_province()
        # 存在省存在市，市属于省
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        for child in self.partner.child_ids:
            child.address_id.city_id = city.id
            child.address_id.city_id.onchange_province()
        # 存在省存在市存在县，但县不属于市
        county = self.env['all.county'].search([('county_name', '=', u'太康县')])
        for child in self.partner.child_ids:
            child.address_id.county_id = county.id
            child.address_id.county_id.onchange_province()
        # 存在省存在市存在县，县属于市
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        for child in self.partner.child_ids:
            child.address_id.county_id = county.id
            child.address_id.county_id.onchange_province()

    def test_onchange_city(self):
        '''测试onchange city'''
        # 不存在市
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市不存在省
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        self.partner.city_id = city.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市不存在省，不存在县
        self.partner.county_id = False
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市存在省存在县，但县不属于市
        self.partner.province_id = False
        county = self.env['all.county'].search(
                [('county_name', '=', u'承德县')])
        self.partner.county_id = county.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市不存在省，存在县，县属于市
        self.partner.province_id = False
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        self.partner.county_id = county.id
        self.partner.city_id = city.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市存在省
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        self.partner.province = province.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市存在省存在县，县属于市
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        self.partner.county_id = city.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市存在省存在县，县属于市，但省与  市所在的省相同
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        self.partner.city_id = city.id
        self.partner.province_id = province.id
        self.partner.county_id = county.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市存在省存在县，县属于市，但省与  市所在的省不同
        province = self.env['country.state'].search([('name', '=', u'四川省')])
        self.partner.province_id = province.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市存在省存在县，但县不属于市
        county = self.env['all.county'].search([('county_name', '=', u'承德县')])
        self.partner.county_id = county.id
        self.partner.province_id = province.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市存在省存在县，县不属于市，省与  市所在的省不同
        province = self.env['country.state'].search([('name', '=', u'四川省')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        county = self.env['all.county'].search([('county_name', '=', u'承德县')])
        self.partner.city_id = city.id
        self.partner.county_id = county.id
        self.partner.province_id = province.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市存在省存在县，县不属于市，但省与  市所在的省相同
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        county = self.env['all.county'].search([('county_name', '=', u'承德县')])
        self.partner.city_id = city.id
        self.partner.province_id = province.id
        self.partner.county_id = county.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市存在省不存在县，省与  市所在的省不同
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        province = self.env['country.state'].search([('name', '=', u'山西省')])
        self.partner.city_id = city.id
        self.partner.county_id = False
        self.partner.province_id = province.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()
        # 存在市存在省不存在县，省与  市所在的省相同
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        self.partner.city_id = city.id
        self.partner.county_id = False
        self.partner.province_id = province.id
        for child in self.partner.child_ids:
            child.address_id.onchange_city()

    def test_onchange_county(self):
        '''测试onchange county'''
        county = self.env['all.county'].search([('county_name', '=', u'正定县')])
        self.partner.county_id = county.id
        for child in self.partner.child_ids:
            child.address_id.onchange_county()

class test_partner(TransactionCase):

    def setUp(self):
        '''准备数据'''
        super(test_partner, self).setUp()
        self.partner_id = self.env.ref('core.jd')

    def test_compute_partner_address(self):
        '''测试如果业务伙伴地址中有默认地址，则显示在业务伙伴列表上'''
        partner =  self.env['partner'].search(
                    [('id', '=', self.partner_id.id)])
        for child in partner.child_ids:
            child.address_id.detail_address = u'金海路1688号'
        partner._compute_partner_address()
        for child in partner.child_ids:
            child.contact_people = u'小李'
            child.mobile = 13849898888
            child.phone = 66889922
            child.qq = 23455443
            child.address = u'金海路1688号'
            child.is_default_add = True
        partner._compute_partner_address()
#         self.assertEqual(partner.contact_people, u'小李')
#         self.assertEqual(partner.mobile, 13849898888)
#         self.assertEqual(partner.phone, 66889922)
#         self.assertEqual(partner.qq, 23455443)
#         self.assertEqual(partner.contact_people, u'金海路1688号')
