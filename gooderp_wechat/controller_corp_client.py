# -*- coding: utf-8 -*-

import os
import sys
from contextlib import closing
import math
import jinja2
import hashlib
import time
import werkzeug.utils
import datetime
import openerp
import simplejson
from openerp import http
from openerp.http import request
from openerp.modules.registry import RegistryManager
from reportlab.graphics.barcode import createBarcodeDrawing
from openerp.addons.wechat.enterprise import WxApi, WxApplication, WxTextResponse, WxNewsResponse, WxArticle, WxLink
from openerp.addons.website_mshop.pools import ModelPool, CursorProxy, common_functions, PageProxy, _slug
from openerp.addons.dftg_weixin.application.application_test import WxAppCropTest
import pytz


ISODATEFORMAT = '%Y-%m-%d'
ISODATETIMEFORMAT = "%Y-%m-%d %H:%M:%S"
SUPERUSER_ID = 1

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'html'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('openerp.addons.dftg_weixin', "html")

env = jinja2.Environment('<%', '%>', '${', '}', '%', loader=loader, autoescape=True)


class WeixinAppTestController(http.Controller):
    weixin_app = None

    def __init__(self):
        env.globals['_pool'] = ModelPool()
        env.globals['_cr'] = CursorProxy()
        env.globals['_page'] = PageProxy()
        env.globals['_slug'] = _slug
        env.globals.update(common_functions)
        env.filters['tojson'] = simplejson.dumps
        self.weixin_app = WxAppCropTest()

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
            contacts_obj = openerp.registry(db_name)['weixin.contacts']
            try:
                contacts = contacts_obj.browse(cr, SUPERUSER_ID, int(user_id))
            except ValueError:
                template = env.get_template('no_partner.html')
                return template.render({})

            if contacts.exists():
                if not contacts.partner_id:
                    template = env.get_template('no_partner.html')
                    return template.render({})

        template = env.get_template('binding.html')
        return template.render({
            # 'session': request.session,
            'user_id': user_id,
            'partner': contacts and contacts.partner_id or False,
            'contacts': contacts and contacts.contacts_id or False,
            'user': contacts and contacts.odoo_user_id or False,
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
        db = RegistryManager.get(db_name)
        if not user_id:
            return '{}'

        context = {}
        with closing(db.cursor()) as cr:
            contacts_obj = openerp.registry(db_name)['weixin.contacts']
            user_obj = openerp.registry(db_name)['res.users']
            try:
                contacts = contacts_obj.browse(cr, SUPERUSER_ID, int(user_id), context=context)
            except ValueError:
                return '{}'
            if not contacts.odoo_user_id:
                odoo_user_id = user_obj.create(cr, SUPERUSER_ID, self._prepare_user_vals(contacts.partner_id,
                                                                                         request.session.oauth_uid or user_id),
                                               context=context)
                odoo_user = user_obj.browse(cr, SUPERUSER_ID, odoo_user_id, context=context)
            else:
                odoo_user = contacts.odoo_user_id

            weixin_data = user_obj.auth_oauth_get_weixin(cr, SUPERUSER_ID, request.session.oauth_provider_id,
                                                         request.session.access_token, user_id, context=context)

            odoo_user.write({
                'oauth_uid': request.session.oauth_uid,
                'oauth_access_token': request.session.oauth_access_token,
                'oauth_provider_id': request.session.oauth_provider_id,
                'mobile': contacts.mobile,
                'weixin_id': weixin_data.get('weixinid'),
            })

            contacts.write({'is_follow': True, 'weixinid': weixin_data.get('weixinid'), 'odoo_user_id': odoo_user.id})

            cr.commit()
            uid = request.session.authenticate(db_name, odoo_user.login, request.session.oauth_access_token)
            return simplejson.dumps({
                'partner_id': contacts.partner_id.id,
                'uid': uid,
                'login_id': request.session.oauth_uid,
                'is_exists_mobile': True,
                'oauth_access_token': request.session.oauth_access_token,
                'user_id': user_id,
                'mobile': contacts.mobile,
                'access_token': request.session.access_token,
            })

    @http.route('/weixin/old/do_binding', auth='public')
    def do_binding_old(self, mobile, **kw):
        db_name = request.session.db
        db = RegistryManager.get(db_name)
        if not mobile:
            return '{}'

        context = {}
        with closing(db.cursor()) as cr:
            partner_obj = openerp.registry(db_name)['res.partner']
            address_obj = openerp.registry(db_name)['customer.address']
            user_obj = openerp.registry(db_name)['res.users']

            user = None
            partner = None
            address = None

            exits_user_ids = user_obj.search(cr, SUPERUSER_ID,
                                             [('oauth_uid', '=', request.session.oauth_uid or mobile)], limit=1,
                                             context=context)
            if exits_user_ids:
                user = user_obj.browse(cr, SUPERUSER_ID, exits_user_ids[0])
                partner = user.partner_id
            else:
                partner_ids = partner_obj.search(cr, SUPERUSER_ID, [('mobile', '=', mobile)], limit=1, context=context)
                if partner_ids:
                    partner = partner_obj.browse(cr, SUPERUSER_ID, partner_ids[0])

                if not partner or partner.is_company:
                    address_ids = address_obj.search(cr, SUPERUSER_ID, [('mobile_number', '=', mobile)], limit=1,
                                                     context=context)
                    if address_ids:
                        address = address_obj.browse(cr, SUPERUSER_ID, address_ids[0], context=context)
                        partner = address.partner_id

                if not partner:
                    return simplejson.dumps({
                        'no_partner': True,
                    })
                if partner.user_ids:
                    user = partner.user_ids[0]
                else:
                    user_id = user_obj.create(cr, SUPERUSER_ID,
                                              self._prepare_user_vals(partner, request.session.oauth_uid or mobile),
                                              context=context)
                    user = user_obj.browse(cr, SUPERUSER_ID, user_id, context=context)

            if address:
                address.write({'user_id': user.id})

                # partner_id = None
                # partner = None
                # address = None
                # partner_ids = partner_obj.search(cr, SUPERUSER_ID, [('mobile', '=', mobile)], limit=1, context=context)
                # if partner_ids:
                #     partner_id = partner_ids[0]
                #     partner = partner_obj.browse(cr, SUPERUSER_ID, partner_id)

                # #如果没有找到partner，或者partner找到了但是是企业客户，则进行多地址联系人的手机号码查找
                # if not partner_id or (partner_id and partner.is_company):
                #     address_ids = address_obj.search(cr, SUPERUSER_ID, [('mobile_number', '=', mobile)], limit=1, context=context)
                #     if address_ids:
                #         address = address_obj.browse(cr, SUPERUSER_ID, address_ids[0], context=context)
                #         partner = address.partner_id
                #         partner_id = address.partner_id.id

                # #从res.partner找到了对应的partner或者通过多地址找到了partner，都可以继续绑定
                # if partner:
                #     #查找是否存在user
                #     exits_user_ids = user_obj.search(cr, SUPERUSER_ID, [('oauth_uid', '=', mobile)], context=context)
                #     if exits_user_ids:
                #         user_id = exits_user_ids[0]
                #     else:
                #         # 使用request.session.oauth_uid来作为用户的login？
                #         user_id = user_obj.create(cr, SUPERUSER_ID, self._prepare_user_vals(partner, request.session.oauth_uid), context=context)
                #     # 如果存在多地址联系人，则将多地址的联系人关联上user
                #     if address:
                #         address.write({'user_id': user_id})
                # is_share_user = False
                # if partner.is_company:
                #     is_share_user = True
                # 保存用户相关微信登录信息

            user.write({
                'partner_id': partner and partner.id,
                'oauth_uid': request.session.oauth_uid,
                'oauth_access_token': request.session.oauth_access_token or mobile,
                'oauth_provider_id': request.session.oauth_provider_id,
                'mobile': mobile,
                'weixin_id': request.session.weixin_id,
                # 'share': is_share_user
            })

            cr.commit()
            uid = request.session.authenticate(db_name, user.login, request.session.oauth_access_token or mobile)
            return simplejson.dumps({
                'partner_id': partner and partner.id,
                'uid': uid,
                'login_id': request.session.oauth_uid,
                'is_exists_mobile': True,
                'oauth_access_token': request.session.oauth_access_token,
                'user_id': request.session.user_id,
                'access_token': request.session.access_token,
            })

            # return simplejson.dumps({'is_exists_mobile': False})

    # 微信用户取消绑定操作
    @http.route('/weixin/do_cancel_binding', auth='user')
    def do_cancel_binding(self, **kw):
        db_name = request.session.db
        db = RegistryManager.get(db_name)
        result = ''
        with closing(db.cursor()) as cr:
            res_users = openerp.registry(db_name)['res.users']
            # address_obj = openerp.registry(db_name)['customer.address']

            user_ids = res_users.search(cr, SUPERUSER_ID, [('id', '=', request.session.uid)])
            if user_ids:
                user_row = res_users.browse(cr, SUPERUSER_ID, user_ids[0])
                user_row.write({'oauth_access_token': None, 'oauth_uid': None,
                                'oauth_provider_id': None, 'mobile': None, 'weixin_id': None})
                request.session.logout(keep_db=True)
                result = 'OK'

                # if kw.get('address_id'):
                # address_obj.write(cr, SUPERUSER_ID, int(kw.get('address_id')), {'user_id': False})

            cr.commit()

        return simplejson.dumps({'result': result})

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

