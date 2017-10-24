# -*- coding: utf-8 -*-
# © 2016 Elico Corp (www.elico-corp.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models
import report_docx


class IrActionReportDocx(models.Model):
    _inherit = 'ir.actions.report.xml'

    # @api.model
    # def _check_selection_field_value(self, field, value):
    #     if field == 'report_type' and value == 'docx':
    #         return
    #
    #     return super(IrActionReportDocx, self)._check_selection_field_value(
    #         field, value)

    def _lookup_report(self, name):
        self._cr.execute(
            "SELECT * FROM ir_act_report_xml WHERE report_name=%s", (name,))
        r = self._cr.dictfetchone()
        if r:
            if r['report_type'] == 'docx':
                return report_docx.ReportDocx('report.' + r['report_name'], r['model'], register=False)

        return super(IrActionReportDocx, self)._lookup_report(name)
