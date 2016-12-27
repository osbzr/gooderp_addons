# -*- coding: utf-8 -*-

from odoo import api, fields, models


class opportunity(models.Model):
    _name = 'opportunity'
    _inherits = {'task': 'task_id'}
    _inherit = ['mail.thread']
    _order = 'planned_revenue desc, priority desc, id'

    @api.model
    def _select_objects(self):
        records = self.env['business.data.table'].search([])
        models = self.env['ir.model'].search(
            [('model', 'in', [record.name for record in records])])
        return [(model.model, model.name) for model in models]

    task_id = fields.Many2one('task',
                              u'任务',
                              ondelete='cascade',
                              required=True)
    planned_revenue = fields.Float(u'预期收益',
                                   track_visibility='always')
    ref = fields.Reference(string=u'相关记录',
                           selection='_select_objects')

