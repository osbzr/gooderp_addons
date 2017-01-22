# -*- coding: utf-8-*-
from odoo import models, fields,api
from menu import WXMenu
from odoo.exceptions import UserError, ValidationError

# 微信企业号菜单
class wechat_agent_menu(models.Model):
    _name = 'wechat.agent.menu'
    _description = u"微信菜单"

    MENU_TYPE = [
        ('click', u'菜单Key'),
        ('view', u'跳转到网页'),
        ('scancode_push', u'扫描推事件'),
        ('scancode_waitmsg', u'扫描推事件（弹框）'),
        ('pic_sysphoto', u'系统拍照'),
        ('pic_photo_or_album', u'拍照或相册'),
        ('pic_weixin', u'微信发图器'),
        ('location_select', u'地理位置选择器'),
    ]
    @api.multi
    def gather_menu_vals(self):
        res, agent_ids = {}, set()
        for menu in self:
            if menu.menu_level == 'first' and menu.id not in res:
                menu_val = {'name': menu.name}
                if not menu.child_menu_ids:
                    if menu.type == 'view':
                        menu_val.update({'type': 'view', 'url': menu.url})
                    else:
                        menu_val.update({'type': menu.type, 'key': menu.key})
                else:
                    menu_val.update({'sub_button': []})

                res.update({menu.id: menu_val})
            else:
                menu_val = {'name': menu.name, 'type': menu.type}
                if menu.type == 'view':
                    menu_val.update({'url': menu.url})
                else:
                    menu_val.update({'key': menu.key})

                if menu.parent_menu_id.id in res:
                    res[menu.parent_menu_id.id]['sub_button'].append(menu_val)
                else:
                    res.update({
                            menu.parent_menu_id.id: {
                                'name': menu.parent_menu_id.name,
                                'sub_button': [menu_val],
                            }
                        })
            agent_ids.add(menu.agent_id.id)

        if len(agent_ids) != 1:
            raise ValidationError(u'错误', u'只能选择同时同步同一个应用的菜单')

        return agent_ids.pop(), {'button': res.values()}

    def sync_menu(self):
        agent_id, vals = self.gather_menu_vals()
        self._sync_menu(self.agent_id.id, vals)

    def _sync_menu(self,agent_id, vals):
        application_id, access_token = self.get_access_token(agent_id)
        WXMenu.create(access_token, application_id, vals=vals)

    def get_access_token(self, agent_id):
        if agent_id:
            agent = self.env['wechat.application'].browse(agent_id)
            if agent.permission_group_ids and agent.permission_group_ids[0].access_token:
                return agent.application_id, agent.permission_group_ids[0].access_token

        return self._get_agentid(), self._get_access_token()

    def _get_agentid(self):
        """
        :return:  applcation 的application_id
        """
        return False
    def _get_access_token(self):
        """
           :return:  applcation 的 access_token
           """
        return False

    type = fields.Selection(MENU_TYPE, string=u'类型')
    name = fields.Char(u'菜单标题')
    key = fields.Char(u'菜单Key值')
    url = fields.Char(u'网页链接')
    menu_level = fields.Selection([('first', u'一级菜单'), ('second', u'二级菜单')], string=u'菜单等级')
    has_sub_menu = fields.Boolean(u'存在子菜单')
    parent_menu_id = fields.Many2one('wechat.agent.menu', u'上级菜单')
    child_menu_ids = fields.One2many('wechat.agent.menu', 'parent_menu_id', u'子菜单')
    synced = fields.Boolean(u'已同步', copy=False)
    agent_id = fields.Many2one('wechat.application', u'微信应用')

    _defaults = {
        'type': 'view',
        'menu_level': 'first',
        'agent_id': lambda self, cr, uid, ctx=None: ctx.get('active_id'),
    }
