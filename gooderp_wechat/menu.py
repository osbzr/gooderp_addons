#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
from odoo import models
from odoo.exceptions import UserError, ValidationError

class WXMenu:

    BASE_URL = 'https://qyapi.weixin.qq.com/cgi-bin/menu/'
    BASE_CREATE_URL = BASE_URL + 'create?'
    BASE_DELETE_URL = BASE_URL + 'delete?'

    @classmethod
    def create(cls, access_token, agentid, vals=None):
        # 其实创建的时候就会重新删除掉以前的菜单数据

        assert access_token, u'access_token 不存在'
        assert agentid, u'agentid 不存在'
        assert vals, u'创建菜单所需要的数据不存在 不存在'
        vals = json.dumps(vals, ensure_ascii=False)
        vals = vals.encode('utf-8')
        url = cls.BASE_CREATE_URL + 'access_token=' + access_token + '&agentid=%s' % str(agentid)
        res = requests.post(url, data=vals)
        print url
        print vals
        print res.content
        if json.loads(res.content).get('errcode'):
            raise ValidationError(u'错误', u'错误码：%s' % res.content)
