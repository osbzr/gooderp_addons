# -*- coding: utf-8 -*-

import os
import sys
from contextlib import closing
import re,hashlib
import jinja2
import simplejson
import odoo
import time
from odoo import http
from odoo.http import request
from odoo.modules.registry import RegistryManager
from odoo.addons.gooderp_wechat.enterprise import WxApi, WxApplication, WxTextResponse, WxNewsResponse, WxArticle, WxLink
from odoo.addons.core.models.pools import ModelPool, CursorProxy, common_functions, PageProxy, _slug
SUPERUSER_ID = 1

############################################################################################
# 微信企业号"企业小助手"应用消息处理类
# 需要配置wechat.enterprise和wechat.application在data/dftg_corp_weixin.xml文件中
#
class WxAppCropAssistant(WxApplication):

    def __init__(self):
        if self.APP_ID:
            return
        # 取得微信应用配置
        db_name = request.session.db
        db = RegistryManager.get(db_name)
        with closing(db.cursor()) as cr:
            application_id =request.env['ir.model.data'].xmlid_to_res_id('gooderp_weixin.weixin_gooderp_assistant_application')
            if not application_id:
                raise Exception('xmlid not found')
            wechat_application = request.env['wechat.application']
            application = wechat_application.sudo().browse(application_id)
            permission_group_ids = application.permission_group_ids
            if permission_group_ids:
                permission_group = permission_group_ids[0]
                self.SECRET = permission_group.secret
                self.SECRET_TOKEN = application.callback_token
                self.ENCODING_AES_KEY = application.callback_aeskey
                self.APP_ID = application.application_id
                self.CORP_ID = application.enterprise_id.corp_id.encode("ascii")
        self.wxapi = WxApi(self.CORP_ID, self.SECRET)

    #关注事件
    def on_subscribe(self, req):
        res = super(WxAppCropAssistant, self).on_unsubscribe(req)
        db = RegistryManager.get(request.session.db)
        with closing(db.cursor()) as cr:
            contacts_obj = db.get('weixin.contacts')
            try:
                contacts = contacts_obj.browse(cr, SUPERUSER_ID, int(req.FromUserName))
            except ValueError:
                return res
            if contacts.exists():
                contacts.write({'is_follow': True})
            cr.commit()
        return res

    #取消关注事件
    def on_unsubscribe(self, req):
        res = super(WxAppCropAssistant, self).on_unsubscribe(req)
        db = RegistryManager.get(request.session.db)
        with closing(db.cursor()) as cr:
            contacts_obj = db.get('weixin.contacts')
            try:
                contacts = contacts_obj.browse(cr, SUPERUSER_ID, int(req.FromUserName))
            except ValueError:
                return res
            if contacts.exists():
                contacts.write({'is_follow': False})
            cr.commit()
        return res

    # 发送文本回调
    def on_text(self, req):
        # 默认回复同样的文字
        response_content = u'暂不支持此指令'
        self.session_id = False
        self.uid = False
        # 检查临时登录密码，如果找到匹配的，则写入user_id
        re_login_groups = re.match(r'D(\d+)(.*)', req.Content, re.I)
        if re_login_groups and re_login_groups.groups():
            groups = re_login_groups.groups()
            len_groups = len(groups)
            if len_groups > 0:
                temp_password = groups[0]
            if len_groups == 2:
                login = groups[1]
            oauth_uid = req.FromUserName
            weixin_session = request.env['weixin.session'].sudo()
            session_ids = weixin_session.search([('temp_password', '=', temp_password),
                                                                   ('check_time', '=', None)])
            if session_ids:
                session_row = session_ids[0]
                res_users = request.env['res.users'].sudo()
                if login:
                    # oauth_id_is_admin = False
                    oauth_id_user_ids = res_users.search([('oauth_uid', '=', oauth_uid)])
                    if oauth_id_user_ids:
                        oauth_id_user_id = oauth_id_user_ids[0]
                        oauth_id_is_admin = res_users.has_group(oauth_id_user_id, 'base.group_erp_manager')
                        if oauth_id_is_admin:
                            user_ids = res_users.search([('login', '=', login)])
                        else:
                            print u'------ 您没有权限替他人登录'
                    else:
                        print u'------ 您没有绑定账号'
                elif oauth_uid:
                    user_ids = res_users.search([('oauth_uid', '=', oauth_uid)])
                if user_ids:
                    session_row.write({'user_id': user_ids[0].id, 'oauth_uid': oauth_uid})
                    self.session_id = session_row.session_id
                    self.uid = self.check_weixin_session(session_row.session_id)
                    response_content = user_ids[0].name + u' 账号已确认登录'
                else:
                    response_content = u'用户未找到，需要重新绑定账号'
            else:
                response_content = u'请打开登录页面或者再次刷新页面'
        return WxTextResponse(response_content, req)

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

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'html'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.gooderp_weixin', "html")

env = jinja2.Environment('<%', '%>', '${', '}', '%', loader=loader, autoescape=True)


################################################################
# 企业小助手应用微信控制器
#
class WeixinAppAssistantController(http.Controller):
    weixin_app = None
    def __init__(self):
        env.globals['_pool'] = ModelPool()
        env.globals['_cr'] = CursorProxy()
        env.globals['_page'] = PageProxy()
        env.globals['_slug'] = _slug
        env.globals.update(common_functions)
        env.filters['tojson'] = simplejson.dumps
        self.weixin_app = WxAppCropAssistant()
        self.login_user= False
        self.login_session = False
    #微信回调入口网址

    @http.route('/weixin/app/assistant', auth='public', csrf=False)
    def weixin(self, **kw):
        result = self.weixin_app.process(request.httprequest.args, request.httprequest.data)
        self.login_user = self.weixin_app.uid
        self.login_session = self.weixin_app.session_id
        return result

    @http.route('/wechat/pulling', auth='public')
    def wechat_pulling(self, **args):
        user = request.env['res.users'].sudo()
        if self.login_user and request.session.sid == self.login_session:
            users = user.browse(self.login_user)
            self.login_user = False
            self.login_session = False
            uid = request.session.authenticate(request.session.db, users.login, users.oauth_access_token)
            if uid:
                return u'ok'
        return 'error'
