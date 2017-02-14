#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
from odoo.exceptions import UserError, ValidationError
from odoo.addons.gooderp_wechat.ierror import DepartmentExisted_Error, UseridExisted_Error, WeixinidExisted_Error, MobileEXisted_Error, EmailExisted_Error

class WXSyncOperation:

    DEPARTMENT_CREATE = 'https://qyapi.weixin.qq.com/cgi-bin/department/create?'
    DEPARTMENT_UPDATE = 'https://qyapi.weixin.qq.com/cgi-bin/department/update?'
    USER_CREATE = 'https://qyapi.weixin.qq.com/cgi-bin/user/create?'
    USER_UPDATE = 'https://qyapi.weixin.qq.com/cgi-bin/user/update?'
    USER_BASE = 'https://qyapi.weixin.qq.com/cgi-bin/user/'

    @classmethod
    def _check_sync_error(cls, res, name):
        if json.loads(res.content).get('errcode'):
            print res.content
            raise ValidationError(u'错误', u'%s: 错误码：%s' % (name, res.content))

    @classmethod
    def sync_department(cls, access_token, vals=None):
        # 其实创建的时候就会重新删除掉以前的菜单数据
        assert access_token, u'access_token 不存在'
        assert vals, u'创建部门所需要的数据不存在'
        dumps_vals = json.dumps(vals, ensure_ascii=False)
        dumps_vals = dumps_vals.encode('utf-8')
        url = cls.DEPARTMENT_CREATE + 'access_token=' + access_token
        print url, "+----------------"
        res = requests.post(url, data=dumps_vals)
        # 如果要创建的数据已经在微信端存在，那么选择更新它
        if json.loads(res.content).get('errcode') == DepartmentExisted_Error:
            url = cls.DEPARTMENT_UPDATE + 'access_token=' + access_token
            res = requests.post(url, data=dumps_vals)
        # 检测返回的结果中errcode是否存在
        cls._check_sync_error(res, vals.get('name'))

    @classmethod
    def sync_user(cls, access_token, vals=None):
        assert access_token, u'access_token 不存在'
        assert vals, u'同步用户所需要的数据不存在'
        dumps_vals = json.dumps(vals, ensure_ascii=False)
        dumps_vals = dumps_vals.encode('utf-8')
        url = cls.USER_CREATE + 'access_token=' + access_token
        res = requests.post(url, data=dumps_vals)
        # 如果要创建的数据已经在微信端存在，那么选择更新它
        if json.loads(res.content).get('errcode') in (UseridExisted_Error, WeixinidExisted_Error, MobileEXisted_Error, EmailExisted_Error):
            url = cls.USER_UPDATE + 'access_token=' + access_token
            res = requests.post(url, data=dumps_vals)
        # 检测返回的结果中errcode是否存在
        cls._check_sync_error(res, vals.get('name'))

    @classmethod
    def sync_user_by_operation(cls, access_token, vals, operation='create'):
        assert access_token, u'access_token 不存在'
        assert vals, u'同步用户所需要的数据不存在'
        if operation =='batchdelete':
            vals = {"useridlist": vals}
        dumps_vals = json.dumps(vals, ensure_ascii=False)
        dumps_vals = dumps_vals.encode('utf-8')
        url = cls.USER_BASE + operation + '?access_token=' + access_token
        print url,dumps_vals
        res = requests.post(url, data=dumps_vals)
        cls._check_sync_error(res, u'同步用户')
