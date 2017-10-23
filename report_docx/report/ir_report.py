# -*- coding: utf-8 -*-

from odoo import api, models


class IrActionReportDocx(models.Model):
    _inherit = 'ir.actions.report.xml'

    @api.model
    def _check_selection_field_value(self, field, value):
        if field == 'report_type' and value == 'docx':
            return

        return super(IrActionReportDocx, self)._check_selection_field_value(
            field, value)
