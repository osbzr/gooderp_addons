# -*- coding: utf-8 -*-
# © 2016 Elico Corp (www.elico-corp.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests import common
import openerp
import os
import base64
from openerp.addons.report_docx_module.models.parser \
    import ReportDocxReport, ReportDocxParser


class TestReportDocx(common.TransactionCase):
    def setUp(self):
        super(TestReportDocx, self).setUp()
        self.pool = openerp.registry(self.cr.dbname)
        self.path = os.path.dirname(__file__)
        file_path = "%s/data/%s" % (self.path, 'testing_template.docx')
        input_stream = open(file_path, 'rb')
        try:
            self.template = base64.b64encode(input_stream.read())
        finally:
            input_stream.close()

        watermark_template_path = "%s/data/%s" % (self.path, 'watermark.pdf')
        input_stream = open(watermark_template_path, 'rb')
        try:
            self.watermark = base64.b64encode(input_stream.read())
        finally:
            input_stream.close()

    @openerp.tests.common.at_install(False)
    @openerp.tests.common.post_install(True)
    def test_create_docx(self):
        context = {
            'name': 'testing report docx',
            'report_name': 'testing report docx',
            'report_type': 'docx',
            'output_type': 'pdf',
            'model': 'res.groups'
        }
        docx_report_id = self.pool.get('ir.actions.report.xml').create(
            self.cr, 1, context)

        docx_report = self.pool.get('ir.actions.report.xml').browse(
            self.cr, 1, docx_report_id)

        report_engine = ReportDocxReport(
            'report.testing.docx', 'report.docx.template',
            parser=ReportDocxParser
        )
        report_engine.pool = openerp.registry(self.cr.dbname)
        report_engine.name = "1234567" + context['report_name']

        with self.assertRaises(Exception):
            self.report_engine.create(
                self.cr, 1, [self.report_engine.id], {})

            self.assertEqual(
                self.report_engine.title, docx_report.report_name)

    @openerp.tests.common.at_install(False)
    @openerp.tests.common.post_install(True)
    def test_create_not_docx(self):
        context = {
            'name': 'testing report not docx',
            'report_name': 'testing report not docx',
            'report_type': 'pdf',
            'model': 'res.groups'
        }

        docx_report_id = self.pool.get('ir.actions.report.xml').create(
            self.cr, 1, context)

        docx_report = self.pool.get('ir.actions.report.xml').browse(
            self.cr, 1, docx_report_id)

        report_engine = ReportDocxReport(
            'report.testing.not.docx', 'report.docx.template',
            parser=ReportDocxParser
        )
        report_engine.pool = openerp.registry(self.cr.dbname)
        report_engine.name = "1234567" + context['report_name']

        self.assertEqual(
            report_engine.create(
                self.cr, 1, [docx_report_id], {}
            ),
            (False, False)
        )
        self.assertEqual(
            report_engine.title, docx_report.report_name)

    @openerp.tests.common.at_install(False)
    @openerp.tests.common.post_install(True)
    def test_convert_docx_to_pdf_with_watermark_template(self):
        context = {
            'name': 'testing report docx',
            'report_name': 'testing report docx',
            'report_type': 'docx',
            'output_type': 'pdf',
            'model': 'res.groups',
            'watermark_string': 'shadow'
        }
        docx_report_id = self.pool.get('ir.actions.report.xml').create(
            self.cr, 1, context)

        docx_report = self.pool.get('ir.actions.report.xml').browse(
            self.cr, 1, docx_report_id)

        report_engine = ReportDocxReport(
            'report.testing.convert.pdf.template', 'report.docx.template',
            parser=ReportDocxParser
        )
        report_engine.pool = openerp.registry(self.cr.dbname)
        report_engine.name = "1234567" + context['report_name']

        attachment_id = self.pool.get('ir.attachment').create(
            self.cr, 1, {
                'name': 'testing attachment',
                'type': 'binary'
            }
        )

        attachment = self.pool.get('ir.attachment').browse(
            self.cr, 1, attachment_id)
        attachment.db_datas = self.template

        docx_report.template_file = attachment_id

        watermark_id = self.pool.get('ir.attachment').create(
            self.cr, 1, {
                'name': 'watermark',
                'type': 'binary'
            }
        )
        watermark = self.pool.get('ir.attachment').browse(
            self.cr, 1, watermark_id)
        watermark.db_datas = self.watermark

        docx_report.watermark_template = watermark_id

        result = report_engine.create_source_docx(
            self.cr, 1, [1, 2], {
                'active_model': 'res.groups',
                'params': {'action': docx_report_id}
            }
        )

        self.assertEqual(result[1], docx_report.output_type)

        except_file_path = "%s/data/%s" % (
            self.path, 'convert_pdf_watermark_template.pdf')

        input_stream = open(except_file_path, 'rb')
        try:
            except_report = input_stream.read()
        finally:
            input_stream.close()

        self.assertEqual(result[0], except_report)

    @openerp.tests.common.at_install(False)
    @openerp.tests.common.post_install(True)
    def test_convert_docx_to_pdf_with_watermark_string(self):
        context = {
            'name': 'testing report docx',
            'report_name': 'testing report docx',
            'report_type': 'docx',
            'output_type': 'pdf',
            'model': 'res.groups',
            'watermark_string': 'shadow'
        }
        docx_report_id = self.pool.get('ir.actions.report.xml').create(
            self.cr, 1, context)

        docx_report = self.pool.get('ir.actions.report.xml').browse(
            self.cr, 1, docx_report_id)

        report_engine = ReportDocxReport(
            'report.testing.convert.pdf.string', 'report.docx.template',
            parser=ReportDocxParser
        )
        report_engine.pool = openerp.registry(self.cr.dbname)
        report_engine.name = "1234567" + context['report_name']

        attachment_id = self.pool.get('ir.attachment').create(
            self.cr, 1, {
                'name': 'testing attachment',
                'type': 'binary'
            }
        )

        attachment = self.pool.get('ir.attachment').browse(
            self.cr, 1, attachment_id)
        attachment.db_datas = self.template

        docx_report.template_file = attachment_id

        result = report_engine.create_source_docx(
            self.cr, 1, [1, 2], {
                'active_model': 'res.groups',
                'params': {'action': docx_report_id}
            }
        )

        self.assertEqual(result[1], docx_report.output_type)

        except_file_path = "%s/data/%s" % (
            self.path, 'convert_pdf_watermark_string.pdf')

        input_stream = open(except_file_path, 'rb')
        try:
            except_report = input_stream.read()
        finally:
            input_stream.close()

        self.assertEqual(result[0], except_report)

    @openerp.tests.common.at_install(False)
    @openerp.tests.common.post_install(True)
    def test_convert_docx_to_multiple_docx(self):
        context = {
            'name': 'testing report docx',
            'report_name': 'testing report docx',
            'report_type': 'docx',
            'output_type': 'docx',
            'model': 'res.groups'
        }
        docx_report_id = self.pool.get('ir.actions.report.xml').create(
            self.cr, 1, context)

        docx_report = self.pool.get('ir.actions.report.xml').browse(
            self.cr, 1, docx_report_id)
        docx_report.watermark_string = 'shadow'

        report_engine = ReportDocxReport(
            'report.testing.convert.multi.docx', 'report.docx.template',
            parser=ReportDocxParser
        )
        report_engine.pool = openerp.registry(self.cr.dbname)
        report_engine.name = "1234567" + context['report_name']

        with self.assertRaises(Exception):
            report_engine.create_source_docx(
                self.cr, 1, [1, 2], {
                    'active_model': 'res.groups',
                    'params': {'action': docx_report_id}
                }
            )

    @openerp.tests.common.at_install(False)
    @openerp.tests.common.post_install(True)
    def test_convert_docx_to_docx(self):
        context = {
            'name': 'testing report docx',
            'report_name': 'testing report docx',
            'report_type': 'docx',
            'output_type': 'docx',
            'model': 'res.groups'
        }
        docx_report_id = self.pool.get('ir.actions.report.xml').create(
            self.cr, 1, context)

        docx_report = self.pool.get('ir.actions.report.xml').browse(
            self.cr, 1, docx_report_id)
        docx_report.watermark_string = 'shadow'

        report_engine = ReportDocxReport(
            'report.testing.convert.single.docx', 'report.docx.template',
            parser=ReportDocxParser
        )
        report_engine.pool = openerp.registry(self.cr.dbname)
        report_engine.name = "1234567" + context['report_name']

        attachment_id = self.pool.get('ir.attachment').create(
            self.cr, 1, {
                'name': 'testing attachment',
                'type': 'binary'
            }
        )

        attachment = self.pool.get('ir.attachment').browse(
            self.cr, 1, attachment_id)
        attachment.db_datas = self.template

        docx_report.template_file = attachment_id

        result = report_engine.create_source_docx(
            self.cr, 1, [1], {
                'active_model': 'res.groups',
                'params': {'action': docx_report_id}
            }
        )

        self.assertEqual(result[1], docx_report.output_type)
