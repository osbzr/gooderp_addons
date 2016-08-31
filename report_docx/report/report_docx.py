# -*- coding: utf-8 -*-
# © 2016 Elico Corp (www.elico-corp.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.report.report_sxw import report_sxw
from openerp import pooler
import logging
from pyPdf import PdfFileWriter, PdfFileReader
from reportlab.pdfgen import canvas
import os
import base64
from docxtpl import DocxTemplate
from openerp.tools.translate import _
_logger = logging.getLogger(__name__)


class ReportDocx(report_sxw):
    def create(self, cr, uid, ids, data, context=None):
        self.pool = pooler.get_pool(cr.dbname)
        self.cr = cr
        self.uid = uid
        report_obj = self.pool.get('ir.actions.report.xml')
        report_ids = report_obj.search(
            cr, uid, [('report_name', '=', self.name[7:])], context=context)

        if report_ids:
            report_xml = report_obj.browse(
                cr, uid, report_ids[0], context=context)
            self.title = report_xml.name
            if report_xml.report_type == 'docx':
                return self.create_source_docx(cr, uid, ids, context)
        return super(ReportDocx, self).create(cr, uid, ids, data, context)

    def create_source_docx(self, cr, uid, ids, context=None):
        data = self.generate_docx_data(cr, uid, ids, context)

        tmp_folder_name = '/tmp/docx_to_pdf/'
        output_type = self._get_output_type(cr, uid, context)
        output_report = {
            'pdf': 'report.pdf',
            'docx': 'report.docx'
        }

        self._delete_temp_folder(tmp_folder_name)
        self._create_temp_folder(tmp_folder_name)

        self._generate_reports(
            cr, uid, context, tmp_folder_name, data,
            output_type, output_report)

        report = self._get_convert_file(
            tmp_folder_name, output_report[output_type])

        self._delete_temp_folder(tmp_folder_name)

        return (report, output_type)

    def generate_docx_data(self, cr, uid, ids, context):
        """
            Override this method to pass your own data to the engine.
            The return value of this module should be a list with
            report data.
        """
        return [{}]

    def _generate_reports(
        self, cr, uid, context, tmp_folder_name,
        datas, output_type, output_report
    ):
        if "pdf" == output_type:
            self._generate_pdf_reports(
                cr, uid, context, tmp_folder_name, datas,
                output_type, output_report)
            return

        self._generate_doc_reports(
            cr, uid, context, tmp_folder_name, datas,
            output_type, output_report)

    def _generate_pdf_reports(
        self, cr, uid, context, tmp_folder_name,
        datas, output_type, output_report
    ):
        count = 0
        for data in datas:
            self._convert_single_report(
                cr, uid, context, tmp_folder_name, count, data, output_type)
            count = count + 1

        self._combine_pdf_files(
            tmp_folder_name, output_report[output_type])

    def _generate_doc_reports(
        self, cr, uid, context, tmp_folder_name,
        datas, output_type, output_report
    ):
        if len(datas) > 1:
            raise Exception(_(
                "Multiple docx files export doesn't support. " +
                "Please export single docx file."))
        temp_report = self._convert_single_report(
            cr, uid, context, tmp_folder_name, 0, datas[0], output_type)

        cmd = "mv %s %s" % (
            tmp_folder_name + temp_report,
            tmp_folder_name + output_report[output_type])

        os.system(cmd)

    def _combine_pdf_files(self, tmp_folder_name, output_report):
        output_path = tmp_folder_name + output_report
        output_temp_path = tmp_folder_name + 'temp.pdf'

        cmd = "gs -q -dNOPAUSE -sDEVICE=pdfwrite -sOUTPUTFILE=%s \
            -dBATCH %s*water*.pdf" % (output_temp_path, tmp_folder_name)
        os.system(cmd)

        # remove the last empty page
        input_stream = PdfFileReader(file(output_temp_path, 'rb'))
        output_stream = PdfFileWriter()

        pagenum = input_stream.getNumPages()
        for i in range(pagenum - 1):
            page = input_stream.getPage(i)
            output_stream.addPage(page)

        out_stream = file(output_path, 'wb')
        try:
            output_stream.write(out_stream)
        finally:
            out_stream.close()

    def _convert_single_report(
        self, cr, uid, context, tmp_folder_name, count, data, output_type
    ):
        docx_template_name = 'template_%s.docx' % count
        convert_docx_file_name = 'convert_%s.docx' % count
        convert_pdf_file_name = 'convert_%s.pdf' % count
        pdf_file_with_watermark = 'convert_watermark_%s.pdf' % count
        watermark_file = 'watermark.pdf'

        self._convert_docx_from_template(
            cr, uid, data, context,
            tmp_folder_name,
            docx_template_name, convert_docx_file_name)

        if output_type == 'pdf':
            self._convert_docx_to_pdf(
                tmp_folder_name,
                convert_docx_file_name
            )

            self._create_watermark_pdf(
                cr, uid, context,
                tmp_folder_name, watermark_file)

            self._add_watermark_to_pdf(
                tmp_folder_name, watermark_file,
                convert_pdf_file_name, pdf_file_with_watermark
            )

            return pdf_file_with_watermark

        return convert_docx_file_name

    def _convert_docx_from_template(
        self, cr, uid, data, context,
        tmp_folder_name,
        docx_template_name, convert_docx_file_name
    ):
        action_id = context['params']['action']
        action = self.pool.get('ir.actions.report.xml').browse(
            cr, uid, action_id, context)

        template_path = tmp_folder_name + docx_template_name
        convert_path = tmp_folder_name + convert_docx_file_name

        self._save_file(
            template_path, base64.b64decode(action.template_file.datas))

        doc = DocxTemplate(template_path)
        doc.render(data)
        doc.save(convert_path)

    def _convert_docx_to_pdf(
        self, tmp_folder_name,
        convert_docx_file_name
    ):
        docx_path = tmp_folder_name + \
            convert_docx_file_name
        output_path = tmp_folder_name

        cmd = "soffice --headless --convert-to pdf --outdir " + output_path \
            + " " + docx_path
        os.system(cmd)

    def _create_watermark_pdf(
        self, cr, uid, context,
        tmp_folder_name, watermark_file
    ):
        watermark_path = tmp_folder_name + watermark_file
        watermark_string = self._get_watermark_string(cr, uid, context)
        watermark_template = self._get_watermark_template(cr, uid, context)

        if watermark_template:
            self._save_file(
                watermark_path, base64.b64decode(watermark_template))
            return

        self._save_watermark_pdf(watermark_path, watermark_string)

    def _save_watermark_pdf(self, tmp_folder_name, watermark_string):
        wartermark = canvas.Canvas(tmp_folder_name)
        wartermark.setFont("Courier", 60)

        wartermark.setFillGray(0.5, 0.5)

        wartermark.saveState()
        wartermark.translate(500, 100)
        wartermark.rotate(45)
        wartermark.drawCentredString(0, 0, watermark_string)
        wartermark.drawCentredString(0, 300, watermark_string)
        wartermark.drawCentredString(0, 600, watermark_string)
        wartermark.restoreState()
        wartermark.save()

    def _add_watermark_to_pdf(
        self, tmp_folder_name, watermark_file,
        convert_pdf_file, pdf_file_with_watermark
    ):
        watermark_path = tmp_folder_name + \
            watermark_file
        pdf_path = tmp_folder_name + \
            convert_pdf_file
        output_path = tmp_folder_name + \
            pdf_file_with_watermark

        output = PdfFileWriter()
        input_pdf = PdfFileReader(file(pdf_path, 'rb'))
        water = PdfFileReader(file(watermark_path, 'rb'))

        pagenum = input_pdf.getNumPages()

        for i in range(pagenum):
            page = input_pdf.getPage(i)
            page.mergePage(water.getPage(0))
            output.addPage(page)

        out_stream = file(output_path, 'wb')
        try:
            output.write(out_stream)
        finally:
            out_stream.close()

    def _get_convert_file(
        self, tmp_folder_name, convert_file_name
    ):
        path = tmp_folder_name + \
            convert_file_name

        input_stream = open(path, 'r')
        try:
            report = input_stream.read()
        finally:
            input_stream.close()

        return report

    def _get_watermark_string(self, cr, uid, context):
        action_id = context['params']['action']
        action = self.pool.get('ir.actions.report.xml').browse(
            cr, uid, action_id, context)

        if action.watermark_string:
            return action.watermark_string

        return ""

    def _get_watermark_template(self, cr, uid, context):
        action_id = context['params']['action']
        action = self.pool.get('ir.actions.report.xml').browse(
            cr, uid, action_id, context)

        return action.watermark_template.datas

    def _get_output_type(self, cr, uid, context):
        action_id = context['params']['action']
        action = self.pool.get('ir.actions.report.xml').browse(
            cr, uid, action_id, context)

        return action.output_type

    def _create_temp_folder(self, tmp_folder_name):
        cmd = 'mkdir ' + tmp_folder_name
        os.system(cmd)

    def _delete_temp_folder(self, tmp_folder_name):
        cmd = 'rm -rf ' + tmp_folder_name
        os.system(cmd)

    def _save_file(self, folder_name, file):
        out_stream = open(folder_name, 'wb')
        try:
            out_stream.writelines(file)
        finally:
            out_stream.close()
