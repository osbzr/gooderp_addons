# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class Partner(models.Model):
    _inherit = 'partner'

    user_ids = fields.One2many('res.users',
                               'gooderp_partner_id',
                               u'登录用户')

    @api.multi
    def partner_create_user(self):
        ''' 为业务伙伴创建登录用户 '''
        exist_user = self.env['res.users'].search([('login', '=', self.name)])
        if exist_user:
            raise UserError(u'业务伙伴已存在登录用户')
        values = {
            'name': self.name,
            'login': self.name,
            'gooderp_partner_id': self.id,
            'company_id': self.env.user.company_id.id,
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        }
        user = self.env['res.users'].sudo().create(values)
        self.message_post(body=u'登录用户 %s 创建成功。<br>请点击下面链接修改密码 %s' %
                          (user.name, user.signup_url))
        return user
