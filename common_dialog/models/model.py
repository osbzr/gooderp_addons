# -*- coding: utf-8 -*-
from openerp import models


def open_dialog(self, func, options=None):
    context = dict(self.env.context or {})
    context.update(options or {})
    context.update({'func': func})

    if not context.get('message'):
        context['message'] = u'确定吗？'

    return {
        'type': 'ir.actions.act_window',
        'res_model': 'common.dialog.wizard',
        'view_type': 'form',
        'view_mode': 'form',
        'target': 'new',
        'context': context
    }


models.BaseModel.open_dialog = open_dialog
