# -*- coding: utf-8-*-
# from openerp import models,api
from odoo import models, fields

# 微信企业号
class wechat_enterprise(models.Model):
    _name = 'wechat.enterprise'
    _description = u"微信企业号"

    name = fields.Char(u'企业号名称')
    description = fields.Char(u'描述')
    logo = fields.Binary('Logo')
    corp_id = fields.Char(u'CorpID')  # 微信企业号->设置->权限管理->某接口调用权限组->CorpId
    # secret = fields.Char(u'开发者凭据密钥'), #微信企业号->设置->权限管理->某接口调用权限组->开发者凭据密钥Secret
    # access_token = fields.Char(u'微信接口主动调用token'), #7200秒有效
    # access_token_timestamp = fields.Integer(u'token起始时间戳'),
    # jsapi_ticket = fields.Char(u'微信js sdk访问token'), #7200秒有效
    # jsapi_ticket_timestamp = fields.Integer(u'js sdk token起始时间戳'),
    application_ids = fields.One2many('wechat.application', 'enterprise_id', u'企业应用')
    permission_group_ids = fields.One2many('wechat.permission.group', 'enterprise_id', u'权限组')
