# -*- coding: utf-8 -*-

from contextlib import closing
import time
import simplejson
import httplib
import urllib
import threading
import logging
import odoo
from odoo import http
from odoo.http import request
from odoo.api import Environment
from odoo.addons.gooderp_wechat.enterprise import WxApi, WxApplication
from odoo import registry
SUPERUSER_ID = 1
_logger = logging.getLogger(__name__)
# 微信企业号获取access_token处理类
from contextlib import contextmanager
from odoo import api, registry, SUPERUSER_ID

@contextmanager
def environment(db_name):
    """ Return an environment with a new cursor for the current database; the
        cursor is committed and closed after the context block.
    """
    reg = registry(db_name)
    with reg.cursor() as cr:
        yield api.Environment(cr, SUPERUSER_ID, {})
        cr.commit()

class WeixinEnterprise(WxApplication):
    default_interval = 3600  # 每个小时刷新一次所有微信权限组的access_token
    enterprise_id = None
    is_initialized = False
    wxapi = None

    def __init__(self):
        if self.is_initialized:
            return
        self.is_initialized = True
        # 取得微信应用配置
        db_name = request.session.db
        self.enterprise_id = request.env.ref('gooderp_weixin.weixin_gooderp_enterprise')
        wechat_enterprise_obj = request.env['wechat.enterprise']
        wechat_enterprise = wechat_enterprise_obj.sudo().browse(self.enterprise_id.id)
        self.CORP_ID = wechat_enterprise.corp_id.encode("ascii")
        self.group_obj = request.env['wechat.permission.group']
        group_ids = self.group_obj.sudo().search([('enterprise_id', '=', self.enterprise_id.id)])
        groups = self.group_obj.sudo().browse(group_ids)
        found_all_users_group = False
        for group in group_ids:
            if group.code == 'all_users':
                found_all_users_group = True
                self.SECRET = group.secret
                self.wxapi = WxApi(self.CORP_ID, self.SECRET)
        if not found_all_users_group:
            raise Exception("取不到all_users微信权限组")
        # 把groups转为普通的列表对象, 否则在新开的线程中无法使用外面的关闭的cursor
        group_list = []
        for group in group_ids:
            group_list.append({'id': group.id, 'secret': group.secret})
        threaded_http = threading.Thread(target=self.group_loop, args=(db_name,group_list))
        threaded_http.setDaemon(True)
        threaded_http.start()

    # 后台线程获取权限组的access_token
    def group_loop(self, db_name, group_list):
        while True:
            try:
                registry = environment(db_name)
                # 此错误could not serialize access due to concurrent update不是这里的微信更新用户组引起的,而是odoo多tab页更新用户在线状态的固有bug(没什么不好的影响)
                for group in group_list:
                    # 企业默认的授权用户组为最大的那个
                    self.request_weixin(registry,group_id=group.get('id'), secret=group.get('secret'))
                    time.sleep(1)
                time.sleep(self.default_interval)
            except Exception:
                _logger.exception("weixin get token loop error, sleep and retry")
                time.sleep(5)

    # 向微信服务器获取access_token
    def request_weixin(self, registry ,group_id=None, secret=None, context=None):
        with Environment.manage():
            http_client = None
            try:
                #data = {'grant_type': 'client_credential', 'corpid': self.CORP_ID, 'corpsecret': secret}
                params = urllib.urlencode({})
                headers = {"Content-type": "application/x-www-form-urlencoded",
                           "Accept": "text/plain"}
                http_client = httplib.HTTPSConnection("qyapi.weixin.qq.com", timeout=5)
                http_client.request("GET", "/cgi-bin/gettoken?corpid=%s&corpsecret=%s" % (self.CORP_ID, secret), params, headers)
                response = http_client.getresponse()
                if response.status != 200:
                    _logger.error('weixin gettoken error, http status: %s', response.status)
                else:
                    data_string = response.read()
                    _logger.info('get access_token: %s' % data_string)
                    return_data = simplejson.loads(data_string)
                    if return_data.get('errcode'):
                        _logger.error('corpid:%s, corpsecret:%s, get weixin access_token error: %s',
                                      self.CORP_ID, secret, data_string)
                    else:
                        access_token = return_data['access_token']
                        params = urllib.urlencode({})
                        http_client.request("POST", "/cgi-bin/get_jsapi_ticket?access_token=" + access_token, params, headers)
                        response = http_client.getresponse()
                        jsapi_ticket = None
                        if response.status != 200:
                            _logger.error('weixin get_jsapi_ticket error, http status: %s', response.status)
                        else:
                            data_string = response.read()
                            return_data = simplejson.loads(data_string)
                            if return_data.get('errmsg') != 'ok':
                                _logger.error('get_jsapi_ticket error: %s', data_string)
                            else:
                                jsapi_ticket = return_data['ticket']
                        timestamp = int(time.time())
                        res = {
                            'access_token': access_token,
                            'access_token_timestamp': timestamp,
                        }
                        if jsapi_ticket:
                            res.update({
                                'jsapi_ticket': jsapi_ticket,
                                'jsapi_ticket_timestamp': timestamp
                            })
                        _logger.info('refresh access_token: %s' % (res))
                        with registry as env:
                            group_obj = env['wechat.permission.group'].browse(group_id)
                            group_obj.write(res)

            finally:
                if http_client:
                    http_client.close()

#####################################################################
#
# 企业企业号取得access_token
# 公开一个接口，可以返回access_token，使得多人开发的时候都可以正常获取access_token
#
#####################################################################
class weixin_corp_access_token_share(http.Controller):

    def __init__(self):
        self.weixin_enterprise = WeixinEnterprise()

    # 返回微信access_token
    @http.route('/rest/weixin/access_token', auth='public')
    def weixin_access_token(self):
        return self.weixin_token.access_token

    # 返回微信ticket_token
    @http.route('/rest/weixin/ticket_token', auth='public')
    def weixin_ticket_token(self):
        return self.weixin_token.jsapi_ticket
