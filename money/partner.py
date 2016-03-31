# -*- coding: utf-8 -*-

from openerp import models, api

class partner(models.Model):
    _inherit = 'partner'
    _description = u'查看业务伙伴对账单'

    @api.multi
    def partner_statements(self):
        self.ensure_one()
        view = self.env.ref('money.partner_statements_report_wizard_form')

        return {
            'name': u'业务伙伴对账单向导',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view.id, 'form')],
            'res_model': 'partner.statements.report.wizard',
            'type': 'ir.actions.act_window',
            'context': {'default_partner_id': self.id},
            'target': 'new',
        }
