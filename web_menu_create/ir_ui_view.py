# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields


class ir_ui_menu(osv.osv):
    _inherit = 'ir.ui.menu'

    _columns = {
        'create_tag': fields.boolean(u'直接创建'),
    }

    def load_create_tag(self, cr, uid, ids, context=None):
        return [menu.id for menu in self.browse(cr, uid, ids, context=context) if menu.create_tag]
