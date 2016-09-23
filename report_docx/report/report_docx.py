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
from openerp.tools import misc
_logger = logging.getLogger(__name__)

from openerp import models

class DataModelProxy(object):
    '''使用一个代理类，来转发 model 的属性，用来消除掉属性值为 False 的情况
       且支持 selection 字段取到实际的显示值
    '''
    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        temp = getattr(self.data, key)
        field = self.data._fields.get(key)

        if isinstance(temp, models.Model):
            return DataModelProxy(temp)

        if field and field.type == 'selection':
            selection = field.selection
            if isinstance(selection, basestring):
                selection = getattr(self.data, selection)()
            elif callable(selection):
                selection = selection(self.data)

            try:
                return [value for _, value in selection if _ == temp][0]
            except KeyError:
                temp = ''

        return temp or ''

    def __getitem__(self, index):
        '''支持列表取值'''
        return DataModelProxy(self.data[index])

    def __iter__(self):
        '''支持迭代器行为'''
        return IterDataModelProxy(self.data)


class IterDataModelProxy(object):
    '''迭代器类，用 next 函数支持 for in 操作'''
    def __init__(self, data):
        self.data = data
        self.length = len(data)
        self.current = 0

    def next(self):
        if self.current >= self.length:
            raise StopIteration()

        temp = DataModelProxy(self.data[self.current])
        self.current += 1

        return temp


class ReportDocx(report_sxw):
    def create(self, cr, uid, ids, data, context=None):
        self.pool = pooler.get_pool(cr.dbname)

        report_obj = self.pool.get('ir.actions.report.xml')
        report_ids = report_obj.search(
            cr, uid, [('report_name', '=', self.name[7:])], context=context)

        if report_ids:
            report_obj = report_obj.browse(
                cr, uid, report_ids[0], context=context)

            self.title = report_obj.name
            if report_obj.report_type == 'docx':
                return self.create_source_docx(cr, uid, ids, report_obj, context)

        return super(ReportDocx, self).create(cr, uid, ids, data, context)

    def create_source_docx(self, cr, uid, ids, report, context=None):
        data = DataModelProxy(self.get_docx_data(cr, uid, ids, report, context))

        foldname = os.getcwd()
        temp_out_file = os.path.join(foldname, 'temp_out_%s.docx' % os.getpid())

        report_stream = ''
        try:
            doc = DocxTemplate(misc.file_open(report.template_file).name)
            doc.render({'obj': data})
            doc.save(temp_out_file)

            with open(temp_out_file, 'rb') as input_stream:
                report_stream = input_stream.read()
        finally:
            os.remove(temp_out_file)

        return (report_stream, report.report_type)

    def get_docx_data(self, cr, uid, ids, report, context):
        return self.pool.get(report.model).browse(cr, uid, ids, context=context)

    def _save_file(self, folder_name, file):
        out_stream = open(folder_name, 'wb')
        try:
            out_stream.writelines(file)
        finally:
            out_stream.close()
