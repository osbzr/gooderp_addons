# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2012 Domsense srl (<http://www.domsense.com>)
#    Copyright (C) 2012-2013:
#        Agile Business Group sagl (<http://www.agilebg.com>)
#    Copyright (C) 2016 开阖有限公司 (<http://www.osbzr.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
try:
    import json
except ImportError:
    import simplejson as json
import time
import odoo.http as http
from odoo.http import request
from odoo.addons.web.controllers.main import ExcelExport
from odoo import models, fields, api
import xlwt
import xlrd
import datetime
import StringIO
import re
from xlutils.copy import copy
from odoo.tools import misc
from odoo import http
import odoo
import urllib2


class ReportTemplate(models.Model):
    _name = "report.template"
    _description = u'报表模板'

    model_id = fields.Many2one('ir.model', u'模型',required=True)
    file_address = fields.Char(u'模板文件路径',required=True)
    active = fields.Boolean(u'可用', default=True)
    blank_rows = fields.Integer(u'空白行数',required=True)

    @api.model
    def get_time(self, model):
        ISOTIMEFORMAT = "%Y-%m-%d"
        report_model = self.env['report.template'].search(
            [('model_id.model', '=', model)], limit=1)
        file_address = report_model and report_model[0].file_address or False
        blank_rows = report_model and report_model[0].blank_rows or False
        return (str(time.strftime(ISOTIMEFORMAT, time.localtime(time.time()))), file_address,blank_rows)


def content_disposition(filename):
    filename = odoo.tools.ustr(filename)
    escaped = urllib2.quote(filename.encode('utf8'))
    browser = request.httprequest.user_agent.browser
    version = int(
        (request.httprequest.user_agent.version or '0').split('.')[0])
    if browser == 'msie' and version < 9:
        return "attachment; filename=%s" % escaped
    elif browser == 'safari' and version < 537:
        return u"attachment; filename=%s.xls" % filename.encode('ascii', 'replace')
    else:
        return "attachment; filename*=UTF-8''%s.xls" % escaped


class ExcelExportView(ExcelExport, ):
    def __getattribute__(self, name):
        if name == 'fmt':
            raise AttributeError()
        return super(ExcelExportView, self).__getattribute__(name)

    @http.route('/web/export/export_xls_view', type='http', auth='user')
    def export_xls_view(self, data, token):
        data = json.loads(data)
        files_name = data.get('files_name', [])
        columns_headers = data.get('headers', [])
        rows = data.get('rows', [])
        file_address = data.get('file_address', [])

        return request.make_response(
            self.from_data_excel(columns_headers, [rows, file_address]),
            headers=[
                ('Content-Disposition', content_disposition(files_name)),
                ('Content-Type', self.content_type)],
            cookies={'fileToken': token}
        )

    # 修改值

    def setOutCell(self, outSheet, col, row, value):
        """ Change cell value without changing formatting. """

        # 本方法来自 葡萄皮的数据空间[http://biotopiblog.sinaapp.com]
        # 链接http://biotopiblog.sinaapp.com/2014/06/python读写excel如何保留原有格式/
        def _getOutCell(outSheet, colIndex, rowIndex):
            """ HACK: Extract the internal xlwt cell representation. """
            # row = outSheet._Worksheet__rows.get(rowIndex)
            row = outSheet._Worksheet__rows.get(rowIndex)
            if not row:
                return None
            cell = row._Row__cells.get(colIndex)
            return cell

        previousCell = _getOutCell(outSheet, col, row)
        if value:
            outSheet.write(row, col, value)
        # HACK, PART II
        if previousCell:
            newCell = _getOutCell(outSheet, col, row)
            if newCell:
                newCell.xf_idx = previousCell.xf_idx
                # END HACK

    def style_data(self):
        style = xlwt.easyxf(
            'font: bold on,height 300;align: wrap on,vert centre, horiz center;')
        colour_style = xlwt.easyxf('align: wrap yes,vert centre, horiz center;pattern: pattern solid, \
                                   fore-colour light_orange;border: left thin,right thin,top thin,bottom thin')

        base_style = xlwt.easyxf('align: wrap yes,vert centre, horiz left; pattern: pattern solid, \
                                     fore-colour light_yellow;border: left thin,right thin,top thin,bottom thin')
        float_style = xlwt.easyxf('align: wrap yes,vert centre, horiz right ; pattern: pattern solid,\
                                      fore-colour light_yellow;border: left thin,right thin,top thin,bottom thin')
        date_style = xlwt.easyxf('align: wrap yes; pattern: pattern solid,fore-colour light_yellow;border: left thin,right thin,top thin,bottom thin\
                                     ', num_format_str='YYYY-MM-DD')
        datetime_style = xlwt.easyxf('align: wrap yes; pattern: pattern solid, fore-colour light_yellow;\
                                         protection:formula_hidden yes;border: left thin,right thin,top thin,bottom thin',
                                     num_format_str='YYYY-MM-DD HH:mm:SS')
        return style, colour_style, base_style, float_style, date_style, datetime_style

    def from_data_excel(self, fields, rows_file_address):
        rows, file_address = rows_file_address
        if file_address:
            bk = xlrd.open_workbook(misc.file_open(
                file_address).name, formatting_info=True)
            workbook = copy(bk)
            worksheet = workbook.get_sheet(0)
            for i, fieldname in enumerate(fields):
                self.setOutCell(worksheet, 0, i, fieldname)
            for row, row_vals in enumerate(rows):
                for col, col_value in enumerate(row_vals):
                    if isinstance(col_value, basestring):
                        col_value = re.sub("\r", " ", col_value)
                    self.setOutCell(worksheet, col, row + 1, col_value)
        else:
            workbook = xlwt.Workbook()
            worksheet = workbook.add_sheet('Sheet 1')
            style, colour_style, base_style, float_style, date_style, datetime_style = self.style_data()
            worksheet.write_merge(0, 0, 0, len(
                fields) - 1, fields[0], style=style)
            worksheet.row(0).height = 400
            worksheet.row(2).height = 400
            columnwidth = {}
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    if cell_index in columnwidth:
                        if len("%s" % (cell_value)) > columnwidth.get(cell_index):
                            columnwidth.update(
                                {cell_index: len("%s" % (cell_value))})
                    else:
                        columnwidth.update(
                            {cell_index: len("%s" % (cell_value))})
                    if row_index == 0:
                        cell_style = colour_style
                    elif row_index != len(rows) - 1:
                        cell_style = base_style
                        if isinstance(cell_value, basestring):
                            cell_value = re.sub("\r", " ", cell_value)
                        elif isinstance(cell_value, datetime.datetime):
                            cell_style = datetime_style
                        elif isinstance(cell_value, datetime.date):
                            cell_style = date_style
                        elif isinstance(cell_value, float) or isinstance(cell_value, int):
                            cell_style = float_style
                    else:
                        cell_style = xlwt.easyxf()
                    worksheet.write(row_index + 1, cell_index,
                                    cell_value, cell_style)
            for column, widthvalue in columnwidth.items():
                """参考 下面链接关于自动列宽（探讨）的代码
                 http://stackoverflow.com/questions/6929115/python-xlwt-accessing-existing-cell-content-auto-adjust-column-width"""
                if (widthvalue + 3) * 367 >= 65536:
                    widthvalue = 50
                worksheet.col(column).width = (widthvalue + 4) * 367
        # frozen headings instead of split panes
        worksheet.set_panes_frozen(True)
        # in general, freeze after last heading row
        worksheet.set_horz_split_pos(3)
        # if user does unfreeze, don't leave a split there
        worksheet.set_remove_splits(True)
        fp_currency = StringIO.StringIO()
        workbook.save(fp_currency)
        fp_currency.seek(0)
        data = fp_currency.read()
        fp_currency.close()
        return data
