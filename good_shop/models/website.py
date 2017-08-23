# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class website(models.Model):
    _inherit = 'website'

    gooderp_partner_id = fields.Many2one(related='user_id.gooderp_partner_id',
                                         relation='partner',
                                         string=u'Partner')
