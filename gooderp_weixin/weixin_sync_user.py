# -*- coding: utf-8-*-
from odoo import models,api
import json
from odoo.exceptions import UserError, ValidationError

class staff(models.Model):
    _inherit = 'staff'

    DEPARMENT_XMLID = {
        'user': 'gooderp_weixin.weixin_department_user',
    }

    def sync_weixin_contacts(self):
        for staff_row in self:
            if not staff_row.user_id:
                raise ValidationError(u'该员工还没绑定用户！')
            if not staff_row.work_mobile:
                raise ValidationError(u'该员工还没有填写工作手机！')
            weixin_contacts = False
            if staff_row.contacts_ids:
                weixin_contacts = staff_row.contacts_ids[0]
            vals = staff_row._get_vals_by_pratner(weixin_contacts=weixin_contacts)
            staff_row.create_or_update_or_delete_weixin_contacts(vals)
        return True

    def create_or_update_or_delete_weixin_contacts(self, vals):
        if vals.get('sync_status') == 'create':
            weixin_contact_row = self.env['weixin.contacts'].create(vals)
            if weixin_contact_row.staff_id and weixin_contact_row.staff_id.user_id:
                weixin_contact_row.staff_id.user_id.oauth_uid = weixin_contact_row.id
                weixin_contact_row.staff_id.user_id.oauth_access_token = weixin_contact_row.work_mobile
        elif vals.get('sync_status') == 'update':
            if self.contacts_ids[0].sync_status == 'create':
                vals.update({'sync_status': 'create', 'update_list': ''})
            self.contacts_ids[0].write(vals)
        elif vals.get('sync_status') == 'delete':
            self.contacts_ids[0].write(vals)
        return True

    @api.multi
    def _get_vals_by_pratner(self, weixin_contacts=None):
        self.ensure_one()
        for staff_row in self:
            res = {}
            field_list = ['name', 'work_mobile', 'work_email']
            if staff_row.is_arbeitnehmer:
                if weixin_contacts:
                    update_list = []
                    for diff_field in field_list:
                        if getattr(staff_row, diff_field) != getattr(weixin_contacts, diff_field):
                            res.update({diff_field: getattr(staff_row, diff_field)})
                            update_list.append(diff_field)
                    res.update({
                            'update_list': json.dumps(update_list),
                            'sync_status': 'update',
                            'weixin_contacts_id': weixin_contacts.id,
                        })
                else:
                    for field in field_list:
                        res.update({field: getattr(staff_row, field)})
                    res.update({
                            'staff_id': staff_row.id,
                            'user_id': staff_row and staff_row.user_id and staff_row.user_id.id or False,
                            'sync_status': 'create',
                            'origin': 'partner',
                        })
            else:
                if weixin_contacts:
                    res.update({
                        'sync_status': 'delete',
                    })
        return res
