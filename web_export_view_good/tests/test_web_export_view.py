# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.addons.web_export_view_good.controllers.controllers import ExcelExportView, content_disposition
import os
from urllib import urlencode
from odoo.tests.common import HttpCase
import odoo.tests


class TestWebExportViewTwo(TransactionCase):

    def test_web_export_view(self):
        self.env['report.template'].get_time('partner')

        # self.env['report.template'].create({'model': self.env.search([('name', '=', 'partner')]),
        #                                     'file_address': "%s\%s" % (os.path.split(os.path.realpath(__file__))[0], "hello.xls")})
        data = {u'headers': [u'\u5ba2\u6237', u' ', u' ', u' '],
                u'model': u'partner',
                u'rows': [[u'\u5ba2\u6237\u7c7b\u522b', u'\u7f16\u53f7', u'\u540d\u79f0', u'\u5e94\u6536\u4f59\u989d'],
                          [u'\u4e00\u7ea7\u5ba2\u6237', u'jd', u'\u4eac\u4e1c', 0], [u'\u5408\u8ba1', u' ', u' ', 0], [u'\u64cd\u4f5c\u4eba', u'admin', u'\u64cd\u4f5c\u65f6\u95f4', u'2016-05-05']],
                u'file_address': "%s%s" % (os.path.split(os.path.realpath(__file__))[0], "/hello.xls"),
                u'blank_rows':1}
        a = ExcelExportView()
        a.from_data_excel(data.get('headers'), [
                          data.get("rows"), data.get("file_address")])
        data.update({u'rows': [[u'\u5ba2\u6237\u7c7b\u522b', u'\u7f16\u53f7', u'\u540d\u79f0', u'\u5e94\u6536\u4f59\u989d']],
                     u'file_address': "%s%s" % (os.path.split(os.path.realpath(__file__))[0], "/None.xls"),
                     u'blank_rows':1})
        a.from_data_excel(data.get('headers'), [
                          data.get("rows"), data.get("file_address")])
        data_two = {"model": "res.users", "headers": [u"用户", " ", " ", " "],
                    "rows": [[u"名称", u"登录", u"语言", u"最后一次登录"],
                             ["Administrator", "admin",
                                 u"Chinese (CN) / 简体中文", u"2016年05月09日"],
                             ["Demo User", "demo", u"Chinese (CN) / 简体中文", ""],
                             [u"操作人", "admin", u"操作时间", "2016-05-09"]],
                    "file_address": '',
                    "blank_rows":1}
        a.from_data_excel(data_two.get('headers'), [data_two.get("rows"), ''])


class TestReportTemplate(TransactionCase):

    def test_compute_model_name(self):
        template = self.env['report.template'].create(
            {'active': True, 'model_id': self.env.ref('base.model_res_users').id, 'file_address': u'/hello.xls', 'blank_rows':1})
        template.get_time('res.partner')


class WebExportViewTestCase(HttpCase):
    def test_content_dispostion(self):
        data_json = {'data': {}, 'token': 12142432}
        url = '/web/export/export_xls_view'
        self.url_open(url, data=bytes(urlencode(data_json)))
        ee = ExcelExportView()
        data = {'header': 'OKKK'}
        # ee.export_xls_view(json.dumps(data),2131413)
        # request.httprequest.user_agent.browser = 'msie'
        # request.httprequest.user_agent.version ='8'
        # content_disposition('filename')
        #
        # request.httprequest.user_agent.browser = 'safari'
        # request.httprequest.user_agent.version ='8'
        # content_disposition('filename')
        #
        # request.httprequest.user_agent.browser = 'OOO'
        # request.httprequest.user_agent.version ='8'
        # content_disposition('filename')
