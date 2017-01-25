# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class WeiXinLoginBase(http.Controller):
    def __init__(self):
        self.login_user = False
        self.login_session = False

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
