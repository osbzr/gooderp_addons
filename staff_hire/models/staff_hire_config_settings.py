# -*- coding: utf-8 -*-

from odoo import fields, models


class hire_settings(models.TransientModel):
    _name = 'staff.hire.config.settings'
    _inherit = ['res.config.settings']

    module_hire_survey = fields.Selection(selection=[
        (0, "Do not use interview forms"),
        (1, "Use interview forms during the recruitment process")
        ], string='Interview Form')
