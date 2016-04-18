# -*- coding: utf-8-*-
from openerp.exceptions import except_orm
from openerp import models, fields, api

class Country(models.Model):
    _name = 'country'
    _description = u'国家'

    name = fields.Char(u'国家名')
    
class CountryState(models.Model):
    _name = 'country.state'
    _description = u'省'

    country_id = fields.Many2one('country', u'国家')
    name = fields.Char(u'省名')
    code = fields.Char(u'编号')
    city_ids = fields.One2many('all.city', 'province_id', u'城市')


class all_city(models.Model):
    _name = 'all.city'
    _rec_name = 'city_name'
    _description = u'市'
    city_name = fields.Char(u'市')
    country_ids = fields.One2many('all.county', 'city_id', u'县')
    province_id = fields.Many2one('country.state', u'省',
                                  domain="[('country_id.name','=','中国')]")


class all_county(models.Model):
    _name = 'all.county'
    _rec_name = 'county_name'
    _description = u'县'

    city_id = fields.Many2one('all.city', u'城市名称')
    county_name = fields.Char(u'县名称')
    description = fields.Char(u'描述')


class province_city_county(models.Model):
    _name = 'province.city.county'
    _description = u'省市县'

#     @api.onchange('county_id','city_id','province_id')
#     def onchange_province(self):
#         # 为地址填写时方便，当选定省时 ，市区的列表里面只有所选省的
#         if self.province_id:
#             if self.city_id:
#                 city = self.env['all.city'].search([('id', '=', self.city_id.id)])
#                 if city.province_id.id == self.province_id.id:
#                     if self.county_id:
#                         county = self.env['all.county'].search([('id', '=', self.county_id.id)])
#                         if county.city_id.id == self.city_id.id:
#                             return{}
#                     return {'domain': {'city_id': [('province_id', '=', self.province_id.id)]},
#                             'value': {'county_id': ''}}
#                 else:
#                     return {'domain': {'city_id': [('province_id', '=', self.province_id.id)]},
#                             'value': {'city_id': ''}}
#             else:
#                 return {'domain': {'city_id': [('province_id', '=', self.province_id.id)]}}
#         else:
#             return {'domain': {'city_id': [], 'county_id': []},
#                     'value': {'county_id': '', 'city_id': ''}}
#             
#     @api.onchange('county_id','city_id','province_id')
#     def onchange_county(self):
#         # 选定了一个区县，自动填充其所属的省和市
#         if self.county_id:
#             try:
#                 county_obj = self.env['all.county'].search([('id', '=', self.county_id.id)])
#                 city_obj = self.env['all.city'].search([('id', '=', self.city_id.id)])
#                 return {'domain': {'county_id': [('city_id', '=', self.city_id.id)]},
#                         'value': {'city_id': county_obj[0].city_id.id,
#                                   'province_id': city_obj[0].province_id.id}}
#             except Exception:
#                 raise except_orm(u'错误', u"无法根据所选区县填充省和市")
# 
#     @api.onchange('county_id','city_id','province_id')
#     def onchange_city(self):
#         # 为地址填写时方便，当选定市时 ，县区的列表里面只有所选市的
#         if self.city_id:
#             city_obj = self.env['all.city'].search([('id', '=', self.city_id.id)])
#             province_id = city_obj[0].province_id
#             if not self.province_id:
#                 if self.county_id:
#                     county_obj = self.env['all.county'].search([('id', '=', self.county_id.id)])
#                     if county_obj[0].city_id.id == self.city_id.id:
#                         return {'domain': {'county_id': [('city_id', '=', self.city_id.id)]}}
#                     return {'value': {'county_id': "", 'province_id': province_id.id},
#                             'domain': {'county_id': [('city_id', '=', self.city_id.id)]}}
#                 return {'value': {'province_id': province_id.id},
#                         'domain': {'county_id': [('city_id', '=', self.city_id.id)]}}
#             else:
#                 if self.county_id:
#                     county_obj = self.env['all.county'].search([('id', '=', self.county_id.id)])
#                     if county_obj.city_id.id == self.city_id.id:
#                         if province_id.id != self.province_id.id:
#                             return {'domain': {'county_id': [('city_id', '=', self.city_id.id)],
#                                                'city_id': [('province_id', '=', province_id.id)]},
#                                     'value': {'province_id': province_id}}
#                         return {'domain': {'county_id': [('city_id', '=', self.city_id.id)],
#                                            'city_id': [('province_id', '=', province_id.id)]}}
#                     else:
#                         if province_id.id != self.province_id.id:
#                             return {'domain': {'county_id': [('city_id', '=', self.city_id.id)],
#                                                'city_id': [('province_id', '=', province_id.id)]},
#                                     'value': {'province_id': province_id.id, 'county_id': ""}}
#                         return {'domain': {'county_id': [('city_id', '=', self.city_id.id)],
#                                            'city_id': [('province_id', '=', province_id.id)]},
#                                 'value': {'county_id': ""}}
#                 else:
#                     if province_id.id != self.province_id.id:
#                         return {'domain': {'county_id': [('city_id', '=', self.city_id.id)],
#                                            'city_id': [('province_id', '=', province_id.id)]},
#                                 'value': {'province_id': province_id.id}}
#                     return {'domain': {'county_id': [('city_id', '=', self.city_id.id)],
#                                        'city_id': [('province_id', '=', province_id.id)]}}
#         else:
#             return {'domain': {'county_id': []}, 'value': {'county_id': ""}}

    city_id = fields.Many2one('all.city', u'市')
    county_id = fields.Many2one('all.county', u'县')
    province_id = fields.Many2one('country.state', u'省',
                                  domain="[('country_id.name','=','中国')]")


class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'province.city.county']
    _description = u'业务伙伴地址'
 
    address = fields.Char(string=u'地址简称')
    phone = fields.Char(string=u'联系电话')
    mobile = fields.Char(string=u'手机号码')
    zip = fields.Char(string=u'邮政编码')
    contact_people = fields.Char(string=u'联系人')
    is_default_add = fields.Boolean(string=u'是否默认地址', default=False)
    detail_address = fields.Char(string=u'详细地址')

class partner(models.Model):
    _inherit = 'partner'
    _description = u'业务伙伴'

    partner_address = fields.Many2one('res.partner', u'业务伙伴地址')
    city_id = fields.Many2one('all.city', u'市')
    county_id = fields.Many2one('all.county', u'县')
    province_id = fields.Many2one('country.state', u'省',
                                  domain="[('country_id.name','=','中国')]")
