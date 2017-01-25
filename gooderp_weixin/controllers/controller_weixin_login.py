# -*- coding: utf-8 -*-
import os
import sys
import logging
import hashlib
import time
import werkzeug.utils
from contextlib import closing
import jinja2,simplejson
import odoo
from odoo import SUPERUSER_ID
from odoo import http
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home
from odoo.addons.web.controllers.main import  db_monodb, ensure_db, set_cookie_and_redirect, login_and_redirect
from reportlab.graphics.barcode import createBarcodeDrawing
from odoo.addons.gooderp_weixin.controllers.controller_base import WeiXinLoginBase
_logger = logging.getLogger(__name__)

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'html'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.gooderp_weixin', "html")
env = jinja2.Environment('<%', '%>', '${', '}', '%', loader=loader, autoescape=True)

#----------------------------------------------------------
# 重载odoo登录 Controller
#----------------------------------------------------------

class WeixinLogin(Home):

    @http.route(csrf=False)
    def web_login(self, *args, **kw):
        ensure_db()
        if request.httprequest.method == 'GET' and request.session.uid and request.params.get('redirect'):
            # Redirect if already logged in and redirect param is present
            return http.redirect_with_hash(request.params.get('redirect'))
        # 取得客户端ip
        session_md5 = hashlib.md5()
        session_md5.update(request.session.sid)
        request.params.setdefault('session_md5', session_md5.hexdigest())
        temp_password = "%06d" % (abs(hash(session_md5.hexdigest())) % (10 ** 6))
        request.params.setdefault('temp_password', temp_password)
        values = {
            'session_id': request.session.sid,
            'temp_password': temp_password,
        }
        session_obj = request.env['weixin.session'].sudo()
        if not session_obj.search([('temp_password','=',temp_password),('check_time', '=', None)]):
            session_obj.sudo().create(values)
        response = super(WeixinLogin, self).web_login(*args, **kw)
        return response


#----------------------------------------------------------
# 微信统一身份认证登录 Controller
#----------------------------------------------------------

class WeixinLoginController(WeiXinLoginBase):
    #weixin_app = None

    def __init__(self):
        self.login_session = False
        self.login_user = False

    def check_weixin_session(self, session_id):
        weixin_session = request.env['weixin.session'].sudo()
        session_ids = weixin_session.search([('session_id', '=', session_id), ('check_time', '=', None)])
        uid = False
        if session_ids:
            session_row =session_ids[0]
            if session_row.user_id:
                res_users = request.env['res.users'].sudo()
                user_ids = res_users.search([('id', '=', session_row.user_id)])
                if user_ids:
                    uid = request.session.authenticate(request.session.db, user_ids[0].login, user_ids[0].oauth_access_token)
                    if uid is not False:
                        session_row.write({'check_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))})
        return uid
    #####################################################################
    #
    # 通过微信登录odoo确认页面
    # * 此页面在微信浏览器中
    #
    #####################################################################
    @http.route('/weixin/login/<string:sid>', auth='public', csrf=False)
    def weixin_login_confirm(self, **kw):
        oauth_uid = request.session.oauth_uid
        user_id = request.session.uid
        if oauth_uid:
            title = u'扫码登录失败，请先进行账号绑定。'
            res_user = request.env['res.users'].sudo()
            user_ids = res_user.search([('oauth_uid', '=', oauth_uid)])
            if user_ids:
                # 可能微信浏览器session失效，需要重新取得user_id
                user_row = user_ids[0]
                weixin_session = request.env['weixin.session'].sudo()
                session_ids = weixin_session.search([('session_id', '=', kw.get('sid')), ('check_time', '=', None)])
                if session_ids:
                    session_row = session_ids[0]
                    uid = request.session.authenticate(request.session.db, user_row.login,
                                                       user_row.oauth_access_token)
                    if uid is not False:
                        session_row.write(
                                {'check_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))})
                    self.login_user = uid
                    self.login_session = kw.get('sid')
                    title = u'用户' + user_row.login + u'扫码登录成功'
                else:
                    title = u'扫码登录失败，用户session不存在。'
            else:
                title = u'扫码登录失败，用户不存在。'
        else:
            title = u'扫码登录失败，请在微信中扫码'

        template = env.get_template("weixin_login.html")
        return template.render({
            'user_id': user_id,
            'title': title
        })

    #####################################################################
    #
    # 生成session md5 二维码
    #
    #####################################################################
    @http.route('/weixin/weixin_login_qrcode', auth='public', csrf=False)
    def weixin_login_qrcode(self, type, value, width=600, height=100):
        """Contoller able to render barcode images thanks to reportlab.
        Samples:
            <img t-att-src="'/report/barcode/QR/%s' % o.name"/>
            <img t-att-src="'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s' %
                ('QR', o.name, 200, 200)"/>

        :param type: Accepted types: 'Codabar', 'Code11', 'Code128', 'EAN13', 'EAN8', 'Extended39',
        'Extended93', 'FIM', 'I2of5', 'MSI', 'POSTNET', 'QR', 'Standard39', 'Standard93',
        'UPCA', 'USPS_4State'
        """
        weixin_session = request.env['weixin.session'].sudo().search([('temp_password', '=', value),
                                                               ('check_time', '=', None)])
        width, height = int(width), int(height)
        if width > 600:
            width = 600
        if height > 600:
            height = 600
        url = "http://" + request.httprequest.host + "/weixin/login/" + weixin_session[0].session_id
        barcode = createBarcodeDrawing(
            type, value=url, format='png', width=width, height=height
        )
        barcode = barcode.asString('png')
        return request.make_response(barcode, headers=[('Content-Type', 'image/png')])

    def get_message_debug(self, cr, user_id, pool, context):
        kw = {}
        permission_obj = pool.get('wechat.permission.group')
        permission_id = permission_obj.get_authenticate_group(cr, SUPERUSER_ID, context=context)
        permission = permission_obj.browse(cr, SUPERUSER_ID, permission_id, context=context)
        # session的uid不存在的时候？
        if user_id:
            kw.update({'user_id': user_id})
        elif request.session.uid:
            kw.update({'user_id': request.session.uid})
        jsapi_ticket = permission.jsapi_ticket
        timestamp = int(time.time())
        nonce_str = 'Wm3WZYTPz0wzccnW'  # 随机字符串, 没有意义
        url = request.httprequest.url
        string1 = "jsapi_ticket=%s&noncestr=%s&timestamp=%s&url=%s" % (jsapi_ticket, nonce_str, timestamp, url)
        signature = hashlib.sha1(string1).hexdigest()
        kw.update({
            'appid': permission.enterprise_id.corp_id,
            'timestamp': timestamp,
            'nonceStr': nonce_str,
            'signature': signature,
        })
        return kw

