# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.addons.report_docx.report.report_docx import DataModelProxy
from odoo.tools import misc
import tempfile
import shutil
import datetime


from odoo.addons.report_docx.report import report_helper
from docxtpl import DocxTemplate


class TestReportDocx(TransactionCase):

    def setUp(self):
        '''准备数据'''
        super(TestReportDocx, self).setUp()
        self.ir_actions = self.env.ref('sell.report_sell_order_1')
        self.sell_order = self.env.ref('sell.sell_order_1')
        self.report_docx_sell = self.ir_actions._lookup_report('sell.order')

        self.ir_actions_pdf = self.env.ref('sell.report_sell_order_2')
        self.report_pdf_sell = self.ir_actions_pdf._lookup_report('sell.order.pdf')

    def test_lookup_report(self):
        '''测试docx报表模板'''
        self.sell_order.note = u'测试&和<>'
        self.report_docx_sell.create(
            self.cr, self.uid, self.sell_order.id, self.ir_actions, self.env.context)

    def test_lookup_report_many2one(self):
        '''测试docx报表模板many2one字段中含有特殊字符&<>'''
        for line in self.sell_order.line_ids:
            line.goods_id.name = u'鼠标测试&和<>'
        self.report_docx_sell.create(
            self.cr, self.uid, self.sell_order.id, self.ir_actions, self.env.context)

    def test_lookup_report_pdf(self):
        '''测试docx报表模，输出类型为pdf'''
        # 测试create_source_docx
        # self.report_pdf_sell.create(
        #     self.cr, self.uid, self.sell_order.id, self.ir_actions_pdf, self.env.context)

    def test_lookup_report_type_pdf(self):
        '''测试docx报表模，report_type 为pdf'''
        # 模板为pdf类型,测试create
        self.ir_actions_pdf.write({'report_type': 'pdf'})
        self.report_pdf_sell.create(
            self.cr, self.uid, self.sell_order.id, self.ir_actions_pdf, self.env.context)

        # 模板为docx类型,测试create
        self.report_docx_sell.create(self.cr, self.uid,self.sell_order.id, self.ir_actions, self.env.context)

    def test_lookup_report_no_r(self):
        ''' 测试 执行 ir_report '''
        # 测试 执行 ir_report 的 _lookup_report no r
        with self.assertRaises(Exception):
            self.report_pdf_sell_1 = self.ir_actions_pdf._lookup_report(
                'sell.order1')

    def test_get_docx_data(self):
        self.report_docx_sell.get_docx_data(
            self.cr, self.uid, self.ir_actions.id, self.ir_actions, self.env.context)

    def test_save_file(self):
        doxc_file = self.report_docx_sell.create(
            self.cr, self.uid, self.sell_order.id, self.ir_actions, self.env.context)
        tempname = tempfile.mkdtemp()
        shutil.copy(misc.file_open(
            'sell/template/sell.order.docx').name, tempname)
        self.report_docx_sell._save_file(
            tempname + "/sell.order.docx", doxc_file)

    def test_datamodelproxy(self):
        data = DataModelProxy([{"type": 'selection'}])
        data.__getitem__(0)
        data = DataModelProxy([])
        data.__getattr__(0)

    def test_by_selection(self):
        data = DataModelProxy(self.env['home.page'])
        home = self.env['home.page']
        data._compute_by_selection(
            home._fields.get('menu_type'), "all_business")
        home = self.env['sell.order']
        data = DataModelProxy(home)
        data._compute_by_selection(home._fields.get('state'), "done")

    def test_compute_by_datetime(self):
        '''datetime打印处理'''
        obj = self.env['sell.order']
        data = DataModelProxy(obj)
        data._compute_by_datetime(obj._fields.get('create_date'), (datetime.datetime.now()).strftime('%Y-%m-%d %H:%M:%S'))


class TestReportHelper(TransactionCase):
    ''' 测试 ReportHelper '''

    def test_picture(self):
        ''' 测试 把图片的二进制数据（使用了base64编码）转化为一个docx.Document对象 '''
        doc = DocxTemplate(misc.file_open(
            'sell/template/sell.order.docx').name)
        # 读取图片的数据且使用base64编码
        data_1 = open(misc.file_open(
            'core/static/description/logo.png').name, 'rb').read().encode('base64')

        data = self.env['sell.order'].search([('name', '=', 'SO00001')])
        ctx = {'obj': data, 'tpl': doc}

        # not data
        report_helper.picture(ctx, None)
        # not width, height
        report_helper.picture(ctx, data_1)

        # width, height 分别为 'cm'， 'mm'，'inchs'，'pt'，'emu'，'twips'
        # align 分别为'left'，'center'，'center'，'middle'
        report_helper.picture(ctx, data_1, width='122mm')
        report_helper.picture(ctx, data_1, width='12cm',
                              height='12cm', align='left')
        report_helper.picture(ctx, data_1, width='12inchs',
                              height='12inchs', align='left')
        report_helper.picture(ctx, data_1, width='12pt',
                              height='12pt', align='center')
        report_helper.picture(ctx, data_1, width='12emu',
                              height='12emu', align='right')
        report_helper.picture(ctx, data_1, width='12twips',
                              height='12twips', align='middle')
        # width, height 单位不写，为像素
        report_helper.picture(ctx, data_1, width='12',
                              height='12', align='middle')
        # width, height 不是 string 类型 :  not isinstance(s, str)
        report_helper.picture(ctx, data_1, width=12, height=12, align='middle')

    def test_get_env(self):
        ''' 测试 get_env 方法 '''
        doc = DocxTemplate(misc.file_open(
            'sell/template/sell.order.docx').name)
        data = self.env['sell.order'].search([('name', '=', 'SO00001')])

        ctx = {'obj': data, 'tpl': doc}

        jinja_env = report_helper.get_env()
        doc.render(ctx, jinja_env)
