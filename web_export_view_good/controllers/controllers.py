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
import openerp.http as http
from openerp.http import request
from openerp.addons.web.controllers.main import ExcelExport
from openerp import models, fields, api
import xlwt
import xlrd
import datetime
import StringIO
import re
import xlutils.copy


class ReportTemplate(models.Model):
    _name = "report.template"
    model = fields.Many2one('ir.model', u'模块')
    file_address = fields.Char(u'模板文件路径')

    @api.model
    def get_time(self, model):
        ISOTIMEFORMAT = "%Y-%m-%d"
        report_model = self.env['report.template'].search([('model.name', '=', model)])
        file_address = report_model.file_address or False
        return (str(time.strftime(ISOTIMEFORMAT, time.localtime(time.time()))), file_address)


class ExcelExportView(ExcelExport,):

    def __getattribute__(self, name):
        if name == 'fmt':
            raise AttributeError()
        return super(ExcelExportView, self).__getattribute__(name)

    @http.route('/web/export/xls_view', type='http', auth='user')
    def export_xls_view(self, data, token):
        data = json.loads(data)
        model = data.get('model', [])
        columns_headers = data.get('headers', [])
        rows = data.get('rows', [])
        file_address = data.get('file_address', [])
        return request.make_response(
            self.from_data(columns_headers, rows, file_address),
            headers=[
                ('Content-Disposition', 'attachment; filename="%s"'
                 % self.filename(model)),
                ('Content-Type', self.content_type)
            ],
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
        outSheet.write(row, col, value)
        # HACK, PART II
        if previousCell:
            newCell = _getOutCell(outSheet, col, row)
            if newCell:
                newCell.xf_idx = previousCell.xf_idx
        # END HACK

    def from_data(self, fields, rows, file_address):
        if file_address:
            bk = xlrd.open_workbook(file_address, formatting_info=True)
            workbook = xlutils.copy.copy(bk)
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
            base_style = xlwt.easyxf('align: wrap yes')
            date_style = xlwt.easyxf('align: wrap yes', num_format_str='YYYY-MM-DD')
            datetime_style = xlwt.easyxf('align: wrap yes', num_format_str='YYYY-MM-DD HH:mm:SS')

            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    cell_style = base_style
                    if isinstance(cell_value, basestring):
                        cell_value = re.sub("\r", " ", cell_value)
                    elif isinstance(cell_value, datetime.datetime):
                        cell_style = datetime_style
                    elif isinstance(cell_value, datetime.date):
                        cell_style = date_style
                    worksheet.write(row_index + 1, cell_index, cell_value, cell_style)
        fp_currency = StringIO.StringIO()
        workbook.save(fp_currency)
        fp_currency.seek(0)
        data = fp_currency.read()
        fp_currency.close()
        return data
