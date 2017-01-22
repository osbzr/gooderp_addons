# -*- coding: utf-8 -*-

from odoo import models, fields


class weixin_session(models.Model):
    _name = 'weixin.session'

    #session md5
    session_id = fields.Char(u'session')
    #登录名(同user.login)
    username = fields.Char(u'用户名')
    #odoo内部用户id
    user_id = fields.Char(u'用户编号')
    #微信企业号用户id(相当于内部用户id，由微信管理员设置)
    oauth_uid = fields.Char(u'微信用户编号')
    #暂时用微信id代替(相当于微信对外用户id，由用户自己设置)
    oauth_access_token = fields.Char(u'oauth登录token')
    #如果登录成功则写入这个时间，表示这个session已被使用，不能再次登录，否则会自动登录
    check_time = fields.Datetime(u'检查时间')
    #一次性临时登录密码
    temp_password = fields.Char(u'临时登录密码')
