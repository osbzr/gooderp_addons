# -*- coding: utf-8 -*-

import werkzeug.urls
import urlparse
import urllib2,odoo
import simplejson
import hashlib
from odoo import models, fields, api

SUPERUSER_ID = 1


# 用户扩展实现微信回调验证
class res_users(models.Model):
    _inherit = 'res.users'
    # auth_oauth中已经有了用户id: 'oauth_uid': fields.char('OAuth User ID', help="Oauth Provider user_id", copy=False),
    # 企业号微信中下面三个字段必须有一个匹配
    weixin_id = fields.Char(u'微信号', copy=False)
    # 这里的手机号码只是冗余的记录一下，绑定的手机号要比对partner表中的手机号码
    mobile = fields.Char(u'微信手机号码', readonly=True, copy=False)
    # 目前无用
    email = fields.Char(u'微信邮箱', readonly=True, copy=False)

    @api.multi
    def _auth_oauth_rpc(self, endpoint_url, params):
        params_suffix = werkzeug.url_encode(params)
        if urlparse.urlparse(endpoint_url)[4]:
            endpoint_url = endpoint_url + '&' + params_suffix
        else:
            endpoint_url = endpoint_url + '?' + params_suffix

        f = urllib2.urlopen(endpoint_url)
        response = f.read()
        return simplejson.loads(response)

    @api.multi
    def _auth_oauth_validate(self, provider, params):
        self.env.cr.execute("SELECT * FROM auth_oauth_provider WHERE name=%s", (provider,))
        auth_oauth_provider =  self.env.cr.dictfetchone()
        if not auth_oauth_provider:
            raise Exception('Not found auth_oauth_provider: %s', provider)
        wechat_permission_group_id = auth_oauth_provider.get('wechat_permission_group_id')
        permission = self.env['wechat.permission.group'].browse(wechat_permission_group_id)
        # 仅仅获取user_id就可以了
        data_user = self._auth_oauth_rpc(auth_oauth_provider.get('validation_endpoint'), {
                'access_token': permission.access_token,
                'code': params.get('code'),
                'agentid': params.get('agentid')
            })
        if data_user.get('errcode'):
            raise Exception('_auth_oauth_rpc return error: %s', data_user.get('errmsg'))
        #用户token原来是用微信UserID(也就是partner_id)，改成md5加密
        oauth_access_token = ''
        if data_user.get('UserId'):
            oauth_access_token_md5 = hashlib.md5()
            oauth_access_token_md5.update('800890' + data_user.get('UserId') + 'gooderp')
            oauth_access_token = oauth_access_token_md5.hexdigest()

        return {
            'access_token': permission.access_token,
            'jsapi_ticket': permission.jsapi_ticket,
            'oauth_access_token': oauth_access_token,
            'oauth_provider_id': auth_oauth_provider.get('id'),
            'user_id': data_user.get('UserId'),
        }

    @api.multi
    def auth_oauth_get_weixin(self, provider_id, access_token, user_id):
        provider = self.pool.get('auth.oauth.provider').browse(provider_id)

        return self._auth_oauth_rpc(provider.validation_endpoint,
            {'access_token': access_token, 'userid': user_id})

    @api.multi
    def _auth_oauth_signin(self, validation):
        #如果取不到user_id，说明没有完成绑定，则返回False
        if not (validation.has_key('user_id') and validation.get('user_id')):
            return False
        try:
            contacts = self.env['weixin.contacts'].browse(int(validation.get('user_id')))
        except ValueError:
            return False
        if contacts.exists():
            return {
                'partner_id': contacts.staff_id.id,
                'contacts_id': contacts.id,
                'login': contacts.user_id and contacts.user_id.login or '',
                'oauth_uid': validation.get('user_id', ''),
            }
        return False

    @api.multi
    def auth_oauth(self,provider, params):
        validation = self._auth_oauth_validate(provider, params)
        user = self._auth_oauth_signin(validation)
        # return {'validation': validation, 'user': user}
        return validation, user

    @api.model
    def check_credentials(self,password):
        try:
            return super(res_users, self).check_credentials(password)
        except odoo.exceptions.AccessDenied:
            # 这里的password暂时是微信帐号
            res = self.sudo().search([('id', '=', self.env.uid), ('oauth_access_token', '=', password)])
            if not res:
                raise


class auth_oauth_provider(models.Model):
    _inherit = 'auth.oauth.provider'
    # 'access_token': fields.char(u'微信接口主动调用token'), #7200秒有效
    # 'access_token_timestamp': fields.integer(u'token起始时间戳'),
    # 'jsapi_ticket': fields.char(u'微信js sdk访问token'), #7200秒有效
    # 'jsapi_ticket_timestamp': fields.integer(u'js sdk token起始时间戳'),
    # 'gettoken_endpoint' : fields.char(u'取得token URL'), #取得token
    #
    # 'secret': fields.char(u'开发者凭据密钥'), #开发者凭据密钥
    # 'AES_key': fields.char(u'微信AES key'), #微信AES加密key
    # 'agent_id': fields.char(u'应用模块ID'), #对应微信自定义的应用的ID
    wechat_permission_group_id = fields.Many2one('wechat.permission.group', u'权限组')

