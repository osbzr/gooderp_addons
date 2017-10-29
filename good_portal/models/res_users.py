# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    gooderp_partner_id = fields.Many2one('partner',
                                         u'对应业务伙伴')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        args.append(('share','=',False))
        return super(ResUsers, self).name_search(name=name, args=args, operator=operator, limit=limit)
