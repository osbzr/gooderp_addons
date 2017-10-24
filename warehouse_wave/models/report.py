# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
import datetime


class ReportWave(models.AbstractModel):
    _name = 'report.warehouse_wave.report_wave_view'
    _template = None
    _wrapped_report_class = None

    @api.multi
    def render_html(self, docids, data=None):
        Report = self.env['report']
        records = self.env['wave'].browse(docids)

        docargs = {
            'doc_ids': self._ids,
            'doc_model': 'wave',
            'docs': records,
            'data': data,
            'datetime': datetime
        }
        return Report.render('warehouse_wave.report_wave_view', docargs)
