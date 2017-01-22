# -*- coding: utf-8-*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
# 微信企业号菜单
class sync_menu_wizard(models.TransientModel):
    _name = 'sync.menu.wizard'
    _description = u"微信菜单同步操作"

    def _check_menu_vals(self, vals):
        if 'button' not in vals:
            raise ValidationError(u'错误', u'生成的同步信息错误，无法同步')
        if len(vals['button']) > 3:
            raise ValidationError(u'错误', u'一级菜单不应该超过三个')
        for menu in vals['button']:
            if 'sub_button' in menu and len(menu['sub_button']) > 5:
                raise ValidationError(u'错误', u'二级此单不应该超过5个')
        return True

    @api.multi
    def sync_menu(self):
        context = self.env.context or {}
        active_ids = self.env.context.get('active_ids')
        model = self.env[self.env.context.get('active_model')]
        if isinstance(model, object) and active_ids:
            agent_id, vals = model.browse(active_ids).gather_menu_vals()
            self._check_menu_vals(vals)
            for menu in model.browse(active_ids):
                menu._sync_menu(menu.agent_id.id, vals)
                menu.synced = True
            # 将所有同步的菜单标记为已同步，其他的菜单全部变成未同步
            unsync_menu_ids = model.search([('id', 'not in', active_ids)])
            unsync_menu_ids.write({'synced': False})
        else:
            raise ValidationError(u'错误', u'没有选中任何需要同步的数据')
