# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaveBomMemory(models.TransientModel):
    _name = 'save.bom.memory'
    _description = u'另存为新的物料清单'

    name = fields.Char(u'物料清单名称')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def save_bom(self):
        for bom in self:
            models = self.env[self.env.context.get('active_model')].browse(
                self.env.context.get('active_ids'))
            return models.save_bom(bom.name)
