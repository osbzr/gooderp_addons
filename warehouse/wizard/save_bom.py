# -*- coding: utf-8 -*-
from odoo import models, fields, api


class save_bom_memory(models.TransientModel):
    _name = 'save.bom.memory'

    name = fields.Char(u'物料清单名称')

    @api.multi
    def save_bom(self):
        for bom in self:
            models = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_ids'))
            return models.save_bom(bom.name)
