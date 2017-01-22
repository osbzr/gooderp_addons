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
from odoo.modules.registry import RegistryManager
from odoo.addons.web.controllers.main import  db_monodb, ensure_db, set_cookie_and_redirect, login_and_redirect
from reportlab.graphics.barcode import createBarcodeDrawing
from odoo.addons.gooderp_weixin.application.application_assistant import WxAppCropAssistant
from odoo.exceptions import UserError, ValidationError
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
        remote_addr = request.httprequest.remote_addr
        # 取得session md5
        # 取得session md5
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

class WeixinLoginController(http.Controller):
    weixin_app = None

    def __init__(self):
        self.weixin_app = WxAppCropAssistant()

    #####################################################################
    #
    # 查是否微信登录
    #
    #####################################################################
    @http.route('/weixin/check_weixin_session', auth='public', csrf=False)
    def check_weixin_session(self, **kw):
        registry, cr, uid, context = request.registry, request.cr, request.session.uid, request.context
        weixin_session = registry.get('weixin.session')
        session_md5 = hashlib.md5()
        session_md5.update(request.session.sid)
        session_ids = weixin_session.search(cr, SUPERUSER_ID, [('session_id', '=', session_md5.hexdigest()), ('check_time', '=', None)])
        result = 'ERROR'
        if session_ids:
            session_row = weixin_session.browse(cr, SUPERUSER_ID, session_ids[0])
            if session_row.user_id:
                res_users = registry.get('res.users')
                user_ids = res_users.search(cr, SUPERUSER_ID, [('id', '=', session_row.user_id)])

                if user_ids:

                    user_objs = res_users.browse(cr, SUPERUSER_ID, user_ids[0])
                        # if not user_objs.has_group('dftg_ext.outer_access'):
                        #     return '您没有权限从外部登录ERP系统，请联系系统管理员!'
                    user_row = res_users.browse(cr, SUPERUSER_ID, user_ids[0])
                    uid = request.session.authenticate(request.session.db, user_row.login, user_row.oauth_access_token)
                    if uid is not False:
                        session_row.write({'check_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))})
                        cr.commit()
                        result = "OK"
                else:
                    result = u'找不到用户%s，请联系系统管理员!session_row.user_id=' % (session_row.user_id)
            else:
                result = u'请关闭浏览器重新打开或者刷新页面再试一次'
        else:
            result = u'请关闭浏览器重新打开或者刷新页面再试一次'
        return result

    #####################################################################
    #
    # 通过微信登录odoo确认页面
    # * 此页面在微信浏览器中
    #
    #####################################################################
    @http.route('/weixin/login/<string:sid>', auth='weixin', csrf=False)
    def weixin_login_confirm(self, **kw):
        db_name = request.session.db
        sid = kw.get('sid')
        oauth_uid = request.session.oauth_uid
        user_id = request.session.uid
        title = ''
        # 如果微信中已经登录过，则提示登录成功
        if oauth_uid:
            db = RegistryManager.get(db_name)
            title = u'扫码登录失败，请先进行账号绑定。'
            with closing(db.cursor()) as cr:
                res_user = db.get('res.users')
                user_ids = res_user.search(cr, 1, [('oauth_uid', '=', oauth_uid)])
                if user_ids:
                    # 可能微信浏览器session失效，需要重新取得user_id
                    user_id = user_ids[0]
                    db_user = res_user.browse(cr, SUPERUSER_ID, user_id)
                    weixin_session = odoo.registry(db_name)['weixin.session']
                    session_ids = weixin_session.search(cr, SUPERUSER_ID, [('session_id', '=', sid)])
                    if session_ids:
                        session_row = weixin_session.browse(cr, SUPERUSER_ID, session_ids[0])
                        session_row.write({'username': db_user.login, 'oauth_access_token': db_user.oauth_access_token,
                                           'user_id': user_id, 'oauth_uid': oauth_uid, 'check_time': None})
                        cr.commit()
                        title = u'用户' + db_user.login + u'扫码登录成功'
                        db.get('bus.bus').sendone(cr, user_id, 'weixin_login', {'sid': sid})

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
        session_md5 = hashlib.md5()
        session_md5.update(request.session.sid)
        if value != session_md5.hexdigest():
            return 'error'
        weixin_session = request.env['weixin.session'].sudo()
        temp_password = "%06d" % (abs(hash(value)) % (10 ** 6))  # int(hashlib.sha1(value).hexdigest(), 16) % (10 ** 6)
        #如果session_id hash后有重复的hash值，则进行删除后再新增
        values = {
            'session_id': value,
            'temp_password': temp_password,
        }
        width, height = int(width), int(height)
        if width > 600:
            width = 600
        if height > 600:
            height = 600
        url = "http://" + request.httprequest.host + "/weixin/login/" + value
        barcode = createBarcodeDrawing(
            type, value="12345767", format='png', width=width, height=height
        )
        barcode = barcode.asString('png')
        return request.make_response(barcode, headers=[('Content-Type', 'image/png')])
        # return img


    # 微信用户绑定
    # 开启微信二次验证，让用户确认一下绑定的partner或者联系人
    @http.route('/weixin/binding', auth='public')
    def binding(self, **kw):
        cr, db_name, user_id = request.cr, request.session.db, request.session.user_id
        oauth_uid = request.session.oauth_uid
        if not oauth_uid and not 'agentid' in kw:
            url = self.weixin_app.oauth_authorize_redirect_url(db_name, request.httprequest.host + '/weixin/binding',
                                                               {})
            return werkzeug.utils.redirect(url)
        contacts = False
        if user_id:
            contacts_obj = request.env['weixin.contacts'].sudo()
            try:
                contacts = contacts_obj.browse(int(user_id))
            except ValueError:
                template = env.get_template('no_partner.html')
                return template.render({})

            if contacts.exists():
                if not contacts.staff_id:
                    template = env.get_template('no_partner.html')
                    return template.render({})

        template = env.get_template('binding.html')
        return template.render({
            # 'session': request.session,
            'user_id': user_id,
            'partner': contacts and contacts.staff_id or False,
            'contacts': contacts,
            'user': contacts and contacts.user_id or False,
            'attention': contacts and contacts.is_follow or False,
        })


    def _prepare_user_vals(self, partner, oauth_uid):
        vals = {
            'name': partner.name,
            'login': oauth_uid,
            'partner_id': partner.id,
        }

        if partner.is_company:
            vals.update({
                'sel_groups_5': False,
                'in_group_1': True,
            })

        return vals


    # @正翔 微信用户绑定操作
    # @张旭 每个微信用户都对应一个user，但同一个企业的user的partner_id都相同，user根据手机号码查找
    @http.route('/weixin/do_binding', auth='public')
    def do_binding(self, user_id, **kw):
        db_name = request.session.db
        if not user_id:
            return '{}'
        context = {}
        contacts_obj = request.env['weixin.contacts']
        user_obj = request.env['res.users']
        try:
            contacts = contacts_obj.browse(int(user_id))
        except ValueError:
            return '{}'
        if not contacts.user_id:
            odoo_user_id = user_obj.create(self._prepare_user_vals(contacts.partner_id,
                                                                                     request.session.oauth_uid or user_id))
            odoo_user = user_obj.browse(odoo_user_id)
        else:
            odoo_user = contacts.odoo_user_id

        weixin_data = user_obj.auth_oauth_get_weixin(request.session.oauth_provider_id,
                                                     request.session.access_token, user_id)

        odoo_user.write({
            'oauth_uid': request.session.oauth_uid,
            'oauth_access_token': request.session.oauth_access_token,
            'oauth_provider_id': request.session.oauth_provider_id,
            'mobile': contacts.work_mobile,
            'weixin_id': weixin_data.get('weixinid'),
        })

        contacts.write({'is_follow': True, 'weixinid': weixin_data.get('weixinid'), 'odoo_user_id': odoo_user.id})
        uid = request.session.authenticate(db_name, odoo_user.login, request.session.oauth_access_token)
        return simplejson.dumps({
            'partner_id': contacts.staff_id.id,
            'uid': uid,
            'login_id': request.session.oauth_uid,
            'is_exists_mobile': True,
            'oauth_access_token': request.session.oauth_access_token,
            'user_id': user_id,
            'mobile': contacts.work_mobile,
            'access_token': request.session.access_token,
        })

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
        # import ipdb
        # ipdb.set_trace()

        kw.update({
            'appid': permission.enterprise_id.corp_id,
            'timestamp': timestamp,
            'nonceStr': nonce_str,
            'signature': signature,
        })
        return kw

