# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    gooderp_partner_id = fields.Many2one('partner',
                                         u'对应业务伙伴')
