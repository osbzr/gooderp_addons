# -*- coding: utf-8-*-
from odoo import models, fields
from urlparse import urlparse
from odoo.exceptions import UserError, ValidationError

# 微信企业号应用
class wechat_application(models.Model):
    _name = 'wechat.application'
    _description = u"微信应用"

    enterprise_id = fields.Many2one('wechat.enterprise', u'企业号', required=True)
    name = fields.Char(u'应用名称')
    description = fields.Char(u'介绍')
    logo = fields.Binary('Logo')
    application_id = fields.Char(u'微信应用ID')
    callback_mode = fields.Boolean(u'回调模式')
    callback_url = fields.Char(u'回调URL')
    callback_token = fields.Char(u'回调Token')
    callback_aeskey = fields.Char(u'回调EncodingAESKey')
    redirect_domain = fields.Char('可信域名')
    report_location_flag = fields.Selection([('none', u'不上报'), ('enter', u'进入回话上报'),\
         ('continue', u'持续上报')], string=u'上报地理位置')
    is_report_user = fields.Boolean(u'状态变更通知')
    is_report_enter = fields.Boolean(u'上报进入应用事件')
    menu_ids = fields.One2many('wechat.agent.menu', 'agent_id', u'菜单')
    permission_group_ids = fields.Many2many('wechat.permission.group', 'application_permission_ref',
                                            'application_id', 'permission_id', u'相关权限')


    _sql_constraints = [
        ('application_id_uniq', 'unique(enterprise_id, application_id)', '用户企业号中的应用号必须唯一')
    ]

    def get_callback_host(self):
        application_ids = self.search([], limit=1)
        if application_ids:
            url = self.read(application_ids[0], ['callback_url']).get('callback_url')
            if url:
                url = urlparse(url)
                return url.scheme + '://' + url.netloc
            else:
                raise ValidationError(u'错误', u'微信应用中没有设定回调URL')
        else:
            raise ValidationError(u'错误', u'企业号中没有配置应用信息')
