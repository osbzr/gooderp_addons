# -*- coding: utf-8 -*-

from odoo import models, fields

#微信服务号
class wechat_official(models.Model):
    _name = 'wechat.official'
    name = fields.Char(u'微信公众号名称')
    app_id = fields.Char(u'微信接入APP ID') #公众号app ID
    secret = fields.Char(u'开发者凭据密钥') #开发者凭据密钥
    token = fields.Char(u'token') #自定义的token
    access_token = fields.Char(u'微信接口主动调用token') #7200秒有效
    access_token_timestamp = fields.Integer(u'token起始时间戳')
    jsapi_ticket = fields.Char(u'微信js sdk访问token') #7200秒有效
    jsapi_ticket_timestamp = fields.Integer(u'js sdk token起始时间戳')