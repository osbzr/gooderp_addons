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
            weixin_contacts = False
            if staff_row.contacts_ids:
                weixin_contacts = staff.contacts_ids[0]
            vals = staff_row._get_vals_by_pratner(weixin_contacts=weixin_contacts)
            staff_row.create_or_update_weixin_contacts(vals)
            return True

    def create_or_update_weixin_contacts(self, vals):
        print vals
        if vals.get('sync_status') == 'create':
            self.env['weixin.contacts'].create(vals)
        elif vals.get('sync_status') == 'update':
            self.weixin_contacts[0].write(vals)
        return True

    @api.multi
    def _get_vals_by_pratner(self, weixin_contacts=None):
        self.ensure_one()
        for staff_row in self:
            res = {}
            field_list = ['name', 'work_mobile', 'work_email']
            if weixin_contacts:
                update_list = []
                for diff_field in field_list:
                    if getattr(staff_row, diff_field) != getattr(weixin_contacts, diff_field):
                        res.update({diff_field: getattr(staff_row, diff_field)})
                        update_list.append(diff_field)
                res.update({
                        'update_list': json.dumps(update_list),
                        'sync_status': weixin_contacts.sync_status or 'update',
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
        return res
