# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.addons.web_export_view_good.controllers.controllers import ExcelExportView
import os
import openerp.tests


# @openerp.tests.common.at_install(False)
# @openerp.tests.common.post_install(True)
# class TestWebExportView(openerp.tests.HttpCase):

#     def test_web_export_view(self):
#         print "++++"
#         self.phantom_js("/", "openerp.Tour.run('test_export_view', 'test')", "openerp.Tour.tours.test_export_view", login="admin")
#         print "----------"


class TestWebExportViewTwo(TransactionCase):

    def test_web_export_view(self):
        self.env['report.template'].get_time('partner')

        # self.env['report.template'].create({'model': self.env.search([('name', '=', 'partner')]),
        #                                     'file_address': "%s\%s" % (os.path.split(os.path.realpath(__file__))[0], "hello.xls")})
        data = {u'headers': [u'\u5ba2\u6237', u' ', u' ', u' '],
                u'model': u'partner',
                u'rows': [[u'\u5ba2\u6237\u7c7b\u522b', u'\u7f16\u53f7', u'\u540d\u79f0', u'\u5e94\u6536\u4f59\u989d'],
                          [u'\u4e00\u7ea7\u5ba2\u6237', u'jd', u'\u4eac\u4e1c', 0], [u'\u5408\u8ba1', u' ', u' ', 0], [u'\u64cd\u4f5c\u4eba', u'admin', u'\u64cd\u4f5c\u65f6\u95f4', u'2016-05-05']],
                u'file_address': "%s%s" % (os.path.split(os.path.realpath(__file__))[0], "/hello.xls")}
        a = ExcelExportView()
        a.from_data(data.get('headers'), data.get("rows"), data.get("file_address"))
        data.update({u'rows': [[u'\u5ba2\u6237\u7c7b\u522b', u'\u7f16\u53f7', u'\u540d\u79f0', u'\u5e94\u6536\u4f59\u989d']],
                     u'file_address': "%s%s" % (os.path.split(os.path.realpath(__file__))[0], "/None.xls")})
        a.from_data(data.get('headers'), data.get("rows"), data.get("file_address"))
        data_two = {"model": "res.users", "headers": [u"用户", " ", " ", " "],
                    "rows": [[u"名称", u"登录", u"语言", u"最后一次登录"],
                             ["Administrator", "admin", u"Chinese (CN) / 简体中文", u"2016年05月09日"],
                             ["Demo User", "demo", u"Chinese (CN) / 简体中文", ""],
                             [u"操作人", "admin", u"操作时间", "2016-05-09"]],
                    "file_address": ''}
        a.from_data(data_two.get('headers'), data_two.get("rows"), '')
