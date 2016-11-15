# -*- coding: utf-8-*-
from odoo.exceptions import UserError
from odoo import models, fields, api

class Country(models.Model):
    _name = 'country'
    _description = u'国家'

    name = fields.Char(u'国家名')
    
class CountryState(models.Model):
    _name = 'country.state'
    _description = u'省/直辖市/自治区'

    country_id = fields.Many2one('country', u'国家')
    name = fields.Char(u'名称')
    code = fields.Char(u'编号')
    city_ids = fields.One2many('all.city', 'province_id', u'下辖市/区')


class all_city(models.Model):
    _name = 'all.city'
    _rec_name = 'city_name'
    _description = u'地级市'
    city_name = fields.Char(u'名称')
    country_ids = fields.One2many('all.county', 'city_id', u'下辖县/市')
    province_id = fields.Many2one('country.state', u'省/直辖市/自治区',
                                  domain="[('country_id.name','=','中国')]")


class all_county(models.Model):
    _name = 'all.county'
    _rec_name = 'county_name'
    _description = u'县/市/区'

    city_id = fields.Many2one('all.city', u'地级市')
    county_name = fields.Char(u'名称')
    description = fields.Char(u'描述')


class partner_address(models.Model):
    _name = 'partner.address'
    _description = u'业务伙伴的联系人地址'
 
    partner_id = fields.Many2one('partner', u'业务伙伴')
    contact = fields.Char(u'联系人')
    mobile = fields.Char(u'手机')
    phone = fields.Char(u'座机')
    qq = fields.Char(u'QQ/微信')
    province_id = fields.Many2one('country.state', u'省/市',
                                  domain="[('country_id.name','=','中国')]")
    city_id = fields.Many2one('all.city', u'市/区')
    county_id = fields.Many2one('all.county', u'县/市')
    town = fields.Char(u'乡镇')
    detail_address = fields.Char(u'详细地址')
    is_default_add = fields.Boolean(u'是否默认地址')

    @api.onchange('province_id')
    def onchange_province(self):
        # 为地址填写时方便，当选定省时 ，市区的列表里面只有所选省的
        domain_dict = {'city_id': [('province_id', '=', self.province_id.id)]}
        if self.province_id:
            if self.city_id:
                if self.city_id.province_id.id == self.province_id.id:
                    if self.county_id:
                        if self.county_id.city_id.id == self.city_id.id:
                            return{}
                    else:
                        self.county_id = ''
                else:
                    self.city_id = ''
        else:
            self.city_id = ''
            self.county_id = ''
            domain_dict = {'city_id': [], 'county_id': []}

        return {'domain': domain_dict}

    @api.onchange('city_id')
    def onchange_city(self):
        # 为地址填写时方便，当选定市时 ，县区的列表里面只有所选市的
        domain_dict = {'county_id': [('city_id', '=', self.city_id.id)]}
        if self.city_id:
            province = self.city_id.province_id
            if not self.province_id:
                if self.county_id:
                    if self.county_id.city_id.id != self.city_id.id:
                        self.city_id = ''
                        self.province_id = province.id
                else:
                    self.province_id = province.id
            else:
                domain_dict.update({'city_id': [('province_id', '=', province.id)]})
                if self.county_id:
                    if self.county_id.city_id.id == self.city_id.id:
                        if province.id != self.province_id.id:
                            self.province_id = province.id
                    else:
                        if province.id != self.province_id.id:
                            self.province_id = province.id
                            self.county_id = ''
                        else:
                            self.county_id = ''
                else:
                    if province.id != self.province_id.id:
                        self.province_id = province.id
        else:
            self.county_id = ''
            domain_dict = {'county_id': []}

        return {'domain': domain_dict}

    @api.onchange('county_id')
    def onchange_county(self):
        # 选定了一个区县，自动填充其所属的省和市
        if self.county_id:
            self.city_id = self.county_id.city_id.id
            self.province_id = self.city_id.province_id.id
            return {'domain': {'county_id': [('city_id', '=', self.city_id.id)]}}


class partner(models.Model):
    _inherit = 'partner'
    _description = u'业务伙伴'

    @api.one
    @api.depends('child_ids.is_default_add', 'child_ids.province_id', 'child_ids.city_id', 'child_ids.county_id', 'child_ids.town', 'child_ids.detail_address')
    def _compute_partner_address(self):
        '''如果业务伙伴地址中有默认地址，则显示在业务伙伴列表上'''
        if not self.child_ids:
            return {}
        for child in self.child_ids:
            if child.is_default_add:
                self.contact = child.contact
                self.mobile = child.mobile
                self.phone = child.phone
                self.qq = child.qq
                address = '%s%s%s%s%s' % (child.province_id and child.province_id.name or '',
                           child.city_id and child.city_id.city_name or '',
                           child.county_id and child.county_id.county_name or '',
                           child.town or '',
                           child.detail_address or '')
                self.address = address

    child_ids = fields.One2many('partner.address', 'partner_id', u'业务伙伴地址')
    contact = fields.Char(u'联系人', compute='_compute_partner_address')
    mobile = fields.Char(u'手机', compute='_compute_partner_address')
    phone = fields.Char(u'座机', compute='_compute_partner_address')
    qq = fields.Char(u'QQ/微信', compute='_compute_partner_address')
    address = fields.Char(u'送货地址', compute='_compute_partner_address')
