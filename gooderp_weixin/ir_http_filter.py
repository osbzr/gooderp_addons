# -*- coding: utf-8 -*-

import werkzeug.urls
import urllib
import simplejson

from odoo import http
from odoo.http import request
from odoo import models
from odoo.addons.gooderp_wechat.enterprise import WxApi
from application.weixin_enterprise import WeixinEnterprise

SUPERUSER_ID = 1


# 拦截所有HTTP请求，检查是否有微信回调验证参数
# 有验证参数的话则进行验证，验证后跳转到业务页面
class ir_http(models.AbstractModel):
    _inherit = 'ir.http'

    # 微信验证
    def weixin_auth(self, code, state):
        # 自定义菜单中无法用大括号{}符号，用小括号()代替，需要替换
        state = state.replace("'", '"')
        state = state.replace('(', '{')
        state = state.replace(')', '}')
        if state[0] != '{':
            state = '{' + state + '}'
        try:
            state_params = simplejson.loads(state)
        except(Exception):
            raise Exception('weixin state not json: %s' % state)
            return
        httprequest = request.httprequest
        dbname = state_params.get('db') or httprequest.session.db
        if not dbname:
            raise Exception("no dbname!")
        context = state_params.get('c', {})
        provider = 'weixin'
        kw = httprequest.args.to_dict()
        kw.update(state_params)
        validation, user = self.env['res.users'].sudo().auth_oauth(provider, kw)
        uid = False
        if user and 'oauth_uid' in user:
            httprequest.session.oauth_uid = user.get('oauth_uid')
            httprequest.session.login = user.get('login')
            httprequest.session.oauth_access_token = validation.get('oauth_access_token')
            httprequest.session.oauth_provider_id = validation.get('oauth_provider_id')
            httprequest.session.user_id = validation.get('user_id')
            httprequest.session.access_token = validation.get('access_token')
            # 如果没有返回login_id，说明账号没有绑定
            if user.get('login'):
                uid = httprequest.session.authenticate(dbname, user['login'],
                    validation['oauth_access_token'])

        return uid, state_params

    # 重载url分发
    @classmethod
    def _dispatch(self):
        args = request.httprequest.args
        code = args.get('code')
        state = args.get('state')
        if code and state:
            uid, state_params = request.env['ir.http'].weixin_auth(code, state)
            kw = request.httprequest.args.to_dict()
            del kw['code']
            del kw['state']
            if state_params:
                kw.update(state_params)
            # 如果登录成功 # no_binding参数不应该被设置，只有登录后的  # if uid or 'no_binding' in state:
            if uid:
                return werkzeug.utils.redirect(request.httprequest.path + '?' + urllib.urlencode(kw))
            else: # 没有登录成功，说明没有绑定账号，跳转到绑定页面
                return werkzeug.utils.redirect("http://" + request.httprequest.host + "/weixin/binding" +
                                               '?' + urllib.urlencode(kw))
        #检查是否有微信认证
        request.weixin = None
        auth = None
        arguments = {}
        try:
            #这里的arguments只支持传入path_info方式(如/product/<int:product_id>)
            func, arguments = request.env['ir.http']._find_handler()
            auth = func.routing.get('auth')
        except werkzeug.exceptions.NotFound:
            pass
        #if auth == 'weixin' and not request.session.oauth_uid:
        #改成uid判断，否则PC上无法开发测试了
        if auth == 'weixin' and not request.session.uid:
            request.weixin = WeixinEnterprise()
            path = request.httprequest.path
            db_name = request.session.db
            url = request.weixin.oauth_authorize_redirect_url(db_name, request.httprequest.host + path, arguments)
            return werkzeug.utils.redirect(url)
        return super(ir_http, self)._dispatch()

    # 由@http.route注解指定auth='weixin'后自动调用
    def _auth_method_weixin(self):
        if request.weixin and not request.session.oauth_uid:
            raise http.AuthenticationError("Weixin not authentication")
