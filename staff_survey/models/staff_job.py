# -*- coding: utf-8 -*-
from odoo import api, fields, models


class staff_job(models.Model):
    _inherit = "staff.job"

    survey_id = fields.Many2one(
        'survey.survey', u"面试问卷")
