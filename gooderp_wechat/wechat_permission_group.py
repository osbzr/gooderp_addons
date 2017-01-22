# -*- coding: utf-8-*-
from odoo import models, fields
from odoo.exceptions import UserError, ValidationError


# 微信权限组
class wechat_permission_group(models.Model):
    _name = 'wechat.permission.group'
    _description = u"微信权限组"

    name = fields.Char(u'名称')
    code = fields.Char(u'内部编码')
    enterprise_id = fields.Many2one('wechat.enterprise', u'企业号')
    secret = fields.Char(u'开发者凭据密钥')  # 微信企业号->设置->权限管理->某接口调用权限组->开发者凭据密钥Secret
    access_token = fields.Char(u'微信接口主动调用token')  # 7200秒有
    access_token_timestamp = fields.Integer(u'token起始时间戳')
    jsapi_ticket = fields.Char(u'微信js sdk访问token')  # 7200秒有效
    jsapi_ticket_timestamp = fields.Integer(u'js sdk token起始时间戳')
    application_ids = fields.Many2many('wechat.application', 'application_permission_ref', 'permission_id', 'application_id', u'应用权限')
    is_authenticate = fields.Boolean(u'认证组')  # 拥有全用户的授权标记，去这个的access_token去进行用户相关接口操作肯定没错


    def get_access_token_by_code(self,code):
        group_ids = self.search([('code', '=', code)], limit=1, order='id')

        if group_ids:
            vals = self.read(group_ids[0], ['access_token'])
            if vals.get('access_token'):
                return vals.get('access_token')

            raise ValidationError(u'错误', u'该编码所对应的组还没有获得到正确的 access_token')

        raise ValidationError(u'错误', u'不存在一个该编码所对应的组')

    def get_authenticate_access_token(self):
        group_id = self.get_authenticate_group()
        if 'access_token' in group_id:
            return group_id['access_token']
        raise ValidationError(u'错误', u'认证组还没有获得到正确的 access_token')

    def get_authenticate_group(self):
        group_ids = self.search([('is_authenticate', '=', True)], limit=1, order='id')
        if group_ids:
            return group_ids[0]

        raise ValidationError(u'错误', u'不存在一个认证组的权限组')
