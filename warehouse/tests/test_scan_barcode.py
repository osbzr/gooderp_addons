# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestScanBarcode(TransactionCase):

    def setUp(self):
        super(TestScanBarcode, self).setUp()
        self.goods = self.env.ref('goods.computer')
        self.wh_out = self.env.ref('warehouse.wh_out_whout0')

    def test_onchange_scan_barcode_input_code(self):
        """测试扫码onchange"""
        self.wh_out.scan_barcode_input_code = '123456789'
        self.wh_out.onchange_scan_barcode_input_code()
        self.wh_out.scan_barcode_input_code = '123456789 123456789'
        self.wh_out.onchange_scan_barcode_input_code()
        self.wh_out.scan_barcode_input_code = '1111'
        self.wh_out.onchange_scan_barcode_input_code()
