# -*- coding: utf-8 -*-
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
        u'报表类型',
        required=True,
        help="""
            HTML will open the report directly in your browser,
            PDF will use wkhtmltopdf to render the HTML into a PDF file
            and let you download it,
            Controller allows you to define the url of a custom controller
            outputting any kind of report.
            Docx allows you to upload Docx word template in Odoo
            and get it rendered in PDF or docx.
            """)

    template_file = fields.Many2one(
        comodel_name='ir.attachment', string=u'模板')

    watermark_string = fields.Char(string=u'水印文字')

    watermark_template = fields.Many2one(
        comodel_name='ir.attachment', string=u'水印模板')

    output_type = fields.Selection(
        [
            ('pdf', 'PDF'),
            ('docx', 'Docx'),
        ],
        u'打印类型',
        required=True,
        default='pdf')
