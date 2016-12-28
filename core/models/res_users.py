# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError

class res_users(models.Model):
    _inherit = 'res.users'

    employee_ids = fields.One2many('staff', 'user_id', u'对应员工')

    @api.multi
    def write(self, vals):
        res = super(res_users, self).write(vals)
        # 如果普通用户修改管理员，则报错
        if self.env.user.id != 1:
            for record in self:
                if record.id == 1:
                    raise UserError(u'系统用户不可修改')
        # 如果管理员将自己的系统管理权限去掉，则报错
        else:
            if not self.env.user.has_group('base.group_erp_manager'):
                raise UserError(u'不能删除管理员的管理权限')
        return res
