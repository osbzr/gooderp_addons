# -*- coding: utf-8-*-
from odoo import models, api, fields
from odoo.exceptions import UserError, ValidationError

# 微信企业号菜单
class weixin_sync_content(models.TransientModel):
    _name = 'weixin.sync.content'
    _description = u"微信同步操作"

    @api.multi
    def sync_content(self):
        active_ids = self.env.context.get('active_ids')
        model = self.env[self.env.context.get('active_model')]
        staff_model = model.browse(active_ids)
        if active_ids and staff_model:
            staff_model.sync_weixin_contacts()
        else:
            raise ValidationError(u'错误', u'没有选中任何需要同步的数据')
