# -*- coding: utf-8-*-
from odoo import models
from odoo import fields, api

class setting_search(models.Model):
    _name = 'setting.search'

    model_id = fields.Many2one('res.models',u'模型')
    fields_ids = fields.Many2Many()
    show_text = fields.Text(u'显示的样式')
    search_char = fields.Char(u'')