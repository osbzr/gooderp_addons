# -*- coding: utf-8-*-
from odoo import models, api


# 微信企业号菜单
class weixin_diff_contacts(models.TransientModel):
    _name = 'weixin.diff.contacts'
    _description = u"微信本地通讯录同步"

    @api.multi
    def sync_content(self):

        self.env['weixin.contacts'].cron_sync_contacts()
