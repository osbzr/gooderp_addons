# -*- coding: utf-8 -*-
# © 2016 Elico Corp (www.elico-corp.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.report.report_sxw import report_sxw
import logging
import random
from docxtpl import DocxTemplate
from odoo.tools import misc
import ooxml
from ooxml import parse, serialize, importer
import codecs

import pdfkit
_logger = logging.getLogger(__name__)
import pytz

from odoo import models
from odoo import fields
from odoo import api
import tempfile
import os


class DataModelProxy(object):
    '''使用一个代理类，来转发 model 的属性，用来消除掉属性值为 False 的情况
       且支持 selection 字段取到实际的显示值
    '''
    DEFAULT_TZ = 'Asia/Shanghai'

    def __init__(self, data):
        self.data = data

    def _compute_by_selection(self, field, temp):
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

        return temp

    def _compute_by_datetime(self, field, temp):
        if field and field.type == 'datetime' and temp:
            tz = pytz.timezone(
                self.data.env.context.get('tz') or self.DEFAULT_TZ)
            temp_date = fields.Datetime.from_string(temp) + tz._utcoffset
            temp = fields.Datetime.to_string(temp_date)

        return temp

    def _compute_temp_false(self, field, temp):
        if not temp:
            if field and field.type in ('integer', 'float'):
                return 0

        return temp or ''

    def __getattr__(self, key):
        if not self.data:
            return ""
        temp = getattr(self.data, key)
        field = self.data._fields.get(key)

        if isinstance(temp, models.Model):
            return DataModelProxy(temp)

        temp = self._compute_by_selection(field, temp)
        temp = self._compute_by_datetime(field, temp)

        return self._compute_temp_false(field, temp)

    def __getitem__(self, index):
        '''支持列表取值'''
        return DataModelProxy(self.data[index])

    def __iter__(self):
        '''支持迭代器行为'''
        return IterDataModelProxy(self.data)

    def __str__(self):
        '''支持直接在word 上写 many2one 字段'''
        return self.data and self.data.display_name or ''


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
        env = api.Environment(cr, uid, context)
        report_obj = env.get('ir.actions.report.xml')
        report_ids = report_obj.search([('report_name', '=', self.name[7:])])
        self.title = report_ids[0].name
        if report_ids[0].report_type == 'docx':
            return self.create_source_docx(cr, uid, ids, report_ids[0], context)

        return super(ReportDocx, self).create(cr, uid, ids, data, context)

    def generate_temp_file(self, tempname, suffix='docx'):
        return os.path.join(tempname, 'temp_%s_%s.%s' %
                            (os.getpid(), random.randint(1, 10000), suffix))

    def create_source_docx(self, cr, uid, ids, report, context=None):
        data = DataModelProxy(self.get_docx_data(
            cr, uid, ids, report, context))
        tempname = tempfile.mkdtemp()
        temp_out_file = self.generate_temp_file(tempname)

        doc = DocxTemplate(misc.file_open(report.template_file).name)
        # 2016-11-2 支持了图片
        # 1.导入依赖，python3语法
        from . import report_helper
        # 2. 需要添加一个"tpl"属性获得模版对象
        doc.render({'obj': data, 'tpl': doc}, report_helper.get_env())
        doc.save(temp_out_file)

        if report.output_type == 'pdf':
            temp_file = self.render_to_pdf(temp_out_file)
        else:
            temp_file = temp_out_file

        report_stream = ''
        with open(temp_file, 'rb') as input_stream:
            report_stream = input_stream.read()
        os.remove(temp_file)
        return report_stream, report.output_type

    def render_to_pdf(self, temp_file):
        tempname = tempfile.mkdtemp()
        temp_out_file_html = self.generate_temp_file(tempname, suffix='html')
        temp_out_file_pdf = self.generate_temp_file(tempname, suffix='pdf')

        ofile = ooxml.read_from_file(temp_file)
        html = """<html style="height: 100%">
            <head>
                <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"/>
                <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
            </head>
            <body>
            """

        html += unicode(serialize.serialize(ofile.document), 'utf-8')
        html += "</body></html>"

        with codecs.open(temp_out_file_html, 'w', 'utf-8') as f:
            f.write(html)

        pdfkit.from_file(temp_out_file_html, temp_out_file_pdf)

        os.remove(temp_out_file_html)

        return temp_out_file_pdf

    def get_docx_data(self, cr, uid, ids, report, context):
        env = api.Environment(cr, uid, context)
        return env.get(report.model).browse(ids)

    def _save_file(self, folder_name, file):
        out_stream = open(folder_name, 'wb')
        try:
            out_stream.writelines(file)
        finally:
            out_stream.close()
