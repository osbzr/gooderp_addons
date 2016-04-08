# -*- coding: utf-8 -*-

from openerp import models
from openerp import fields
from openerp import api


class ir_ui_menu(models.Model):
    _inherit = 'ir.ui.menu'

    create_tag = fields.Boolean(u'直接创建')

    @api.multi
    def load_create_tag(self):
        return [menu.id for menu in self if menu.create_tag]
