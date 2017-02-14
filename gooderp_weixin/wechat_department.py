# -*- coding: utf-8-*-
from odoo import models, fields, api
from weixin_sync_operation import WXSyncOperation
from odoo.exceptions import UserError, ValidationError

# 微信企业号应用
class wechat_department(models.Model):
    _name = 'wechat.department'
    _description = u"微信应用"
    _order = 'order'
    name = fields.Char(u'名称')
    parentid = fields.Integer(u'父部门id')
    order = fields.Integer(u'次序值')
    department_id = fields.Integer(u'部门id')
    enterprise_id = fields.Many2one('wechat.enterprise', u'企业号')

class wechat_enterprise(models.Model):
    _inherit = 'wechat.enterprise'

    @api.multi
    def sync_department(self):
        access_token = self.env['wechat.permission.group'].get_authenticate_access_token()
        if not access_token:
            raise ValidationError(u'错误', u'没有找到认证组的access_token')
        for enterprise in self:
            for department in enterprise.department_ids:
                res = {
                    'name': department.name,
                    'parentid': department.parentid or 1,
                    'order': department.order,
                    'id': department.department_id,
                }
                WXSyncOperation.sync_department(access_token, res)
    department_ids = fields.One2many('wechat.department', 'enterprise_id', u'组织架构')

