# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase
from psycopg2 import IntegrityError


class test_city_county(TransactionCase):
    '''测试省市县'''
    def test_onchange_province(self):
        '''测试onchange province'''
        partner =  self.env['res.partner'].search([('name', '=', 'Administrator')])
        # 不存在省
        partner.onchange_province()
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        # 存在省不存在市
        partner.province_id = province.id
        partner.onchange_province()
        # 存在省存在市，但市不属于省
        city = self.env['all.city'].search([('city_name', '=', u'上海市')])
        partner.city_id = city.id
        partner.onchange_province()
        # 存在省存在市，市属于省
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        partner.city_id = city.id
        partner.onchange_province()
        # 存在省存在市存在县，但县不属于市
        county = self.env['all.county'].search([('county_name', '=', u'太康县')])
        partner.county_id = county.id
        partner.onchange_province()
        # 存在省存在市存在县，县属于市
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        partner.county_id = county.id
        partner.onchange_province()

    def test_onchange_city(self):
        '''测试onchange city'''
        partner =  self.env['res.partner'].search([('name', '=', 'Administrator')])
        # 不存在市
        partner.onchange_city()
        # 存在市不存在省
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        partner.city_id = city.id
        partner.onchange_city()
        # 存在市不存在省，不存在县
        partner.county_id = False
        partner.onchange_city()
        # 存在市存在省存在县，但县不属于市
        partner.province_id = False
        county = self.env['all.county'].search([('county_name', '=', u'承德县')])
        partner.county_id = county.id
        partner.onchange_city()
        # 存在市不存在省，存在县，县属于市
        partner.province_id = False
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        partner.county_id = county.id
        partner.city_id = city.id
        partner.onchange_city()
        # 存在市存在省
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        partner.province = province.id
        partner.onchange_city()
        # 存在市存在省存在县，县属于市
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        partner.county_id = city.id
        partner.onchange_province()
        # 存在市存在省存在县，县属于市，但省与  市所在的省相同
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        county = self.env['all.county'].search([('county_name', '=', u'平山县')])
        partner.city_id = city.id
        partner.province_id = province.id
        partner.county_id = county.id
        partner.onchange_city()
        # 存在市存在省存在县，县属于市，但省与  市所在的省不同
        province = self.env['country.state'].search([('name', '=', u'四川省')])
        partner.province_id = province.id
        partner.onchange_city()
        # 存在市存在省存在县，但县不属于市
        county = self.env['all.county'].search([('county_name', '=', u'承德县')])
        partner.county_id = county.id
        partner.province_id = province.id
        partner.onchange_city()
        # 存在市存在省存在县，县不属于市，省与  市所在的省不同
        province = self.env['country.state'].search([('name', '=', u'四川省')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        county = self.env['all.county'].search([('county_name', '=', u'承德县')])
        partner.city_id = city.id
        partner.county_id = county.id
        partner.province_id = province.id
        partner.onchange_city()
        # 存在市存在省存在县，县不属于市，但省与  市所在的省相同
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        county = self.env['all.county'].search([('county_name', '=', u'承德县')])
        partner.city_id = city.id
        partner.province_id = province.id
        partner.county_id = county.id
        partner.onchange_city()
        # 存在市存在省不存在县，省与  市所在的省不同
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        province = self.env['country.state'].search([('name', '=', u'山西省')])
        partner.city_id = city.id
        partner.county_id = False
        partner.province_id = province.id
        partner.onchange_city()
        # 存在市存在省不存在县，省与  市所在的省相同
        city = self.env['all.city'].search([('city_name', '=', u'石家庄市')])
        province = self.env['country.state'].search([('name', '=', u'河北省')])
        partner.city_id = city.id
        partner.county_id = False
        partner.province_id = province.id
        partner.onchange_city()

    def test_onchange_county(self):
        '''测试onchange county'''
        partner =  self.env['res.partner'].search([('name', '=', 'Administrator')])
        county = self.env['all.county'].search([('county_name', '=', u'正定县')])
        partner.county_id = county.id
        partner.onchange_county()

class test_partner(TransactionCase):
    def test_onchange_partner(self):
        '''测试partner的onchange'''
        self.env['partner'].onchange_partner_id()
        partner_add = self.env['res.partner'].create(dict(name='jd.add',
                                                          email='d@d'))
        self.env.ref('core.jd').partner_address = partner_add.id
        self.env.ref('core.jd').onchange_partner_id()
