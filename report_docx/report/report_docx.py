# -*- coding: utf-8 -*-

import odoo
from odoo.report.report_sxw import report_sxw
import logging
from pyPdf import PdfFileWriter, PdfFileReader
from reportlab.pdfgen import canvas
import os
import base64
from docxtpl import DocxTemplate
from report_helper import get_env
from lxml import etree
from docx import Document
_logger = logging.getLogger(__name__)


class ReportDocx(report_sxw):
    def create(self, cr, uid, ids, data, context=None):
        env = odoo.api.Environment(cr, uid, context)
        ir_obj = env['ir.actions.report.xml']

        report = ir_obj.search(
            [('report_name', '=', self.name[7:])], limit=1)

        report_type = report.report_type

        if report_type == 'docx':
            return self.create_source_docx(cr, uid, ids, report, data, context)

        return super(ReportDocx, self).create(cr, uid, ids, data, context)

    def create_source_docx(self, cr, uid, ids, report, dict, context=None):
        data = self._generate_docx_data(cr, uid, ids, report, context)

        if not dict.get('template_id', False):
            env = odoo.api.Environment(cr, uid, context)
            ir_obj = env['ir.actions.report.xml']

            report_xml = ir_obj.search(
                [('report_name', '=', self.name[7:])], limit=1)

            dict['template_id'] = report_xml.id

        tmp_folder_name = '/tmp/docx_to_pdf/'
        output_type = self._get_output_type(cr, uid, context, dict)
        output_report = {
            'pdf': 'report.pdf',
            'docx': 'report.docx'
        }

        self._delete_temp_folder(tmp_folder_name)
        self._create_temp_folder(tmp_folder_name)

        self._generate_reports(
            cr, uid, context, tmp_folder_name, data,
            output_type, output_report, dict)

        report = self._get_convert_file(
            tmp_folder_name, output_report[output_type])

        self._delete_temp_folder(tmp_folder_name)

        return (report, output_type)

    def _generate_docx_data(self, cr, uid, ids, report, context):
        env = odoo.api.Environment(cr, uid, context)

        objs = env[report.model].browse(ids)
        convert_data = [self._obj2dict(obj) for obj in objs]
        return convert_data

    def _obj2dict(self, obj):
        memberlist = [m for m in dir(obj) if m[0] != '_' and not callable(m)]
        context = {m: getattr(obj, m) for m in memberlist}
        return context

    def _generate_reports(
        self, cr, uid, context, tmp_folder_name,
        datas, output_type, output_report, dict
    ):
        if "pdf" == output_type:
            self._generate_pdf_reports(
                cr, uid, context, tmp_folder_name, datas,
                output_type, output_report, dict)
            return

        self._generate_doc_reports(
            cr, uid, context, tmp_folder_name, datas,
            output_type, output_report, dict)

    def _generate_pdf_reports(
        self, cr, uid, context, tmp_folder_name,
        datas, output_type, output_report, dict
    ):
        count = 0
        for data in datas:
            self._convert_single_report(
                cr, uid, context, tmp_folder_name,
                count, data, output_type, dict)
            count = count + 1
        self._combine_pdf_files(
            tmp_folder_name, output_report[output_type])

    def _generate_doc_reports(
        self, cr, uid, context, tmp_folder_name,
        datas, output_type, output_report, dict
    ):
        temp_docxs = []
        count = 0
        for data in datas:
            report = self._convert_single_report(
                cr, uid, context, tmp_folder_name,
                count, data, output_type, dict)
            temp_docxs.append(report)
            count = count + 1

        self._combine_docx_files(
            tmp_folder_name, output_report[output_type], temp_docxs)

    def _combine_pdf_files(self, tmp_folder_name, output_report):
        output_path = tmp_folder_name + output_report
        output_temp_path = tmp_folder_name + 'temp.pdf'

        cmd = """gs -q -dNOPAUSE -sDEVICE=pdfwrite -sOUTPUTFILE=%s \
                -dBATCH %s*water*.pdf""" % (output_temp_path, tmp_folder_name)
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

    def _combine_docx_files(self, tmp_folder_name, output_report, temp_docxs):
        output_path = tmp_folder_name + output_report
        first_document = True
        xml_header = ""
        xml_body = ""
        xml_footer = "</w:body>"

        # merge all the reports into first report
        report = Document(tmp_folder_name + temp_docxs[0])

        for file in temp_docxs:
            docx = Document(tmp_folder_name + file)
            xml = etree.tostring(
                docx._element.body, encoding='unicode', pretty_print=False)

            # get the header from first document since
            # all the report have the same format.
            if first_document:
                xml_header = xml.split('>')[0] + '>'
                first_document = False

            for body in etree.fromstring(xml):
                xml_body = xml_body + etree.tostring(body)

        report._element.replace(
            report._element.body, etree.fromstring(
                xml_header + xml_body + xml_footer)
        )

        report.save(output_path)

    def _convert_single_report(
        self, cr, uid, context, tmp_folder_name,
        count, data, output_type, dict
    ):
        docx_template_name = 'template_%s.docx' % count
        convert_docx_file_name = 'convert_%s.docx' % count
        convert_pdf_file_name = 'convert_%s.pdf' % count
        pdf_file_with_watermark = 'convert_watermark_%s.pdf' % count
        watermark_file = 'watermark.pdf'

        self._convert_docx_from_template(
            cr, uid, data, context,
            tmp_folder_name,
            docx_template_name, convert_docx_file_name, dict)

        if output_type == 'pdf':
            self._convert_docx_to_pdf(
                tmp_folder_name,
                convert_docx_file_name
            )

            self._create_watermark_pdf(
                cr, uid, context,
                tmp_folder_name, watermark_file, dict)

            self._add_watermark_to_pdf(
                tmp_folder_name, watermark_file,
                convert_pdf_file_name, pdf_file_with_watermark
            )

            return pdf_file_with_watermark

        return convert_docx_file_name

    def _convert_docx_from_template(
        self, cr, uid, data, context,
        tmp_folder_name,
        docx_template_name, convert_docx_file_name, dict
    ):
        action_id = dict['template_id']
        env = odoo.api.Environment(cr, uid, context)
        action = env['ir.actions.report.xml'].browse(action_id)

        template_path = tmp_folder_name + docx_template_name
        convert_path = tmp_folder_name + convert_docx_file_name

        user = env['res.users'].browse([uid])
        self._save_file(
            template_path, base64.b64decode(action.template_file.datas))

        doc = DocxTemplate(template_path)
        data.update({'tpl': doc})
        jinja_env = get_env()
        doc.render(data, jinja_env)
        doc.save(convert_path)

    def _convert_docx_to_pdf(
        self, tmp_folder_name,
        convert_docx_file_name
    ):
        docx_path = tmp_folder_name + \
            convert_docx_file_name
        output_path = tmp_folder_name

        cmd = "soffice --headless '-env:UserInstallation=" + \
            "file:///tmp/LibreOffice_Conversion_${USER}' " + \
            "--convert-to pdf --outdir " + output_path \
            + " " + docx_path

        os.popen(cmd)

    def _create_watermark_pdf(
        self, cr, uid, context,
        tmp_folder_name, watermark_file, dict
    ):
        watermark_path = tmp_folder_name + watermark_file
        watermark_string = self._get_watermark_string(cr, uid, context, dict)
        watermark_template = self._get_watermark_template(
            cr, uid, context, dict)

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

    def _get_watermark_string(self, cr, uid, context, dict):
        action_id = dict['template_id']
        env = odoo.api.Environment(cr, uid, context)
        action = env['ir.actions.report.xml'].browse(action_id)

        if action.watermark_string:
            return action.watermark_string

        return ""

    def _get_watermark_template(self, cr, uid, context, dict):
        action_id = dict['template_id']
        env = odoo.api.Environment(cr, uid, context)
        action = env['ir.actions.report.xml'].browse(action_id)

        return action.watermark_template.datas

    def _get_output_type(self, cr, uid, context, dict):
        action_id = dict['template_id']
        env = odoo.api.Environment(cr, uid, context)
        action = env['ir.actions.report.xml'].browse(action_id)

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


ReportDocx('report.report.docx', 'report.docx.base')
