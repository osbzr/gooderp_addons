# -*- coding: utf-8 -*-
# © 2016 Elico Corp (www.elico-corp.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class IrActionsReportXml(models.Model):
    _inherit = 'ir.actions.report.xml'

    report_type = fields.Selection(
        [
            ('qweb-pdf', 'PDF'),
            ('qweb-html', 'HTML'),
            ('controller', 'Controller'),
            ('pdf', 'RML pdf (deprecated)'),
            ('sxw', 'RML sxw (deprecated)'),
            ('webkit', 'Webkit (deprecated)'),
            ('docx', 'Docx'),
        ],
        'Report Type', required=True,
        help="""
            HTML will open the report directly in your browser,
            PDF will use wkhtmltopdf to render the HTML into a PDF file
            and let you download it,
            Controller allows you to define the url of a custom controller
            outputting any kind of report."""
    )

    template_file = fields.Char('Template File')
    output_type = fields.Selection(
        [
            ('pdf', 'PDF'),
            ('docx', 'Docx'),
        ],
        'Output Type', required=True, default='docx'
    )
