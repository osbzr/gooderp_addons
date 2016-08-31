# -*- coding: utf-8 -*-
# © 2016 Elico Corp (www.elico-corp.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests import common
import openerp


class TestIrReport(common.TransactionCase):
    def setUp(self):
        super(TestIrReport, self).setUp()

    @openerp.tests.common.at_install(False)
    @openerp.tests.common.post_install(True)
    def test_check_selection_field_value_docx(self):
        module = self.registry('ir.actions.report.xml').browse(self.cr, 1, [1])
        self.assertEqual(module._check_selection_field_value(
            'report_type', 'docx'), None)

    @openerp.tests.common.at_install(False)
    @openerp.tests.common.post_install(True)
    def test_check_selection_field_value_not_docx(self):
        module = self.registry('ir.actions.report.xml').browse(self.cr, 1, [1])

        with self.assertRaises(Exception):
            self.assertEqual(module._check_selection_field_value(
                'report_type', 'None'), None)
