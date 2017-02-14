# -*- coding: utf-8-*-
from odoo import models
from odoo import fields, api
from odoo.exceptions import UserError, ValidationError
from weixin_sync_operation import WXSyncOperation

import json
import logging

_logger = logging.getLogger(__name__)


class staff(models.Model):
    _inherit = 'staff'

    @api.one
    @api.depends('name', 'work_mobile', 'work_email', 'user_id', 'user_id.active')
    def _diff_contacts(self):
        if self.contacts_ids and self.judge_change_staff():
            self.is_weixin_contacts_changed = True
        self.is_weixin_contacts_changed = False

    def judge_change_staff(self):
        diff_fields = ['name', 'work_mobile', 'work_email', 'user_id']
        for fields in diff_fields:
            if self[fields] != self.contacts_ids[0][fields]:
                return True
        return False

    is_weixin_contacts_changed = fields.Boolean(compute='_diff_contacts', default=False,
                                                string=u'微信联系人是否修改')
    contacts_ids = fields.One2many('weixin.contacts', 'staff_id', u'微信联系人')

class weixin_contacts(models.Model):
    _name = 'weixin.contacts'

    @api.multi
    def _get_contacts_by_create(self):
        return {
            'userid': self.id,
            'name': self.name,
            'position': self.position,
            # 'department': self.pool.get('res.partner')._get_department_by_partner(cr, uid, contacts.partner_id),
            'department': self.department,
            'mobile': self.work_mobile,
            'email': self.work_email,
        }

    @api.multi
    def _get_contacts_by_update(self):
        res = {}
        field_dcit={'work_email': 'email', 'work_mobile': 'mobile'}
        if self.update_list:
            update_list = json.loads(self.update_list)
            res = {'userid': self.id}
            for field_name in update_list:
                res.update({field_dcit.get(field_name): getattr(self, field_name)})
        return res

    @api.multi
    def sync_contacts(self):
        cron_contacts_rows = self.search(['|', ('sync_status', '!=', False),
            ('sync_status', '!=', '')], order='sync_status desc')
        return cron_contacts_rows._sync_contacts()

    # 被设计用来作为同步任务的时候调用的函数
    @api.multi
    def cron_sync_contacts(self):
        # 在同步的时候需要再次检查一下是否存在需要同步的数据
        # self.diff_contacts()
        return self.sync_contacts()

    @api.multi
    def _sync_contacts(self):
        access_token = self.env['wechat.permission.group'].get_authenticate_access_token()
        batch_vals = []
        for contacts in self:
            if contacts.sync_status == 'delete':
                batch_vals.append(contacts.id)
            elif contacts.sync_status == 'create':
                try:
                    WXSyncOperation.sync_user_by_operation(access_token, contacts._get_contacts_by_create(), operation='create')
                except Exception, e:
                    raise ValidationError(u'错误, 微信同步用户数量已经超出微信人数上限, %s', e)
                    break
                contacts.write({'sync_status': ''})
            elif contacts.sync_status == 'update':
                WXSyncOperation.sync_user_by_operation(access_token, contacts._get_contacts_by_update(), operation='update')
                contacts.write({'sync_status': ''})
        if batch_vals:
            WXSyncOperation.sync_user_by_operation(access_token, batch_vals, operation='batchdelete')
            self.staff_id.contacts_ids = False
            self.write({'sync_status': '', 'active': False,'staff_id': False})


    staff_id = fields.Many2one('staff', u'业务伙伴', index=True)
    name = fields.Char(u'姓名')
    weixinid = fields.Char(u'微信号')
    work_mobile = fields.Char(u'手机号码', index=True)
    work_email = fields.Char(u'邮箱')
    position = fields.Char(u'职位')
    department = fields.Char(u'部门', default=1)
    user_id = fields.Many2one('res.users', u'odoo用户')
    sync_status = fields.Selection([('create', u'待新建'), ('delete', u'待删除'), ('update', u'待更新')], u'同步状态')
    # 来源字段，记录这条记录是由res.partner还是company.contacts生成的
    is_follow = fields.Boolean(u'是否关注', help=u'根据用户二次验证的消息和用户不关注的消息来更新这个字段值')
    active = fields.Boolean(u'有效', default=True, help=u'如果微信端被删除，则actived置为False，默认值为True（作用是保留微信端被删除的副本）')
    update_list = fields.Char(u'待更新列表')  # 用来记录需要更新的字段列表

    _sql_constraints = [
        ('uniq_mobile', 'UNIQUE(work_mobile)', u'微信通讯录手机号码必须唯一！'),
        ('uniq_mobile', 'UNIQUE(staff_id)', u'每个员工只能有一个微信联系人！')
    ]
