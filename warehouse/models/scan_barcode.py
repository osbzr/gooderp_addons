# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class ScanBarcode(models.Model):
    _name = 'scan.barcode'
    scan_barcode_input_code = fields.Char(string='输入要扫描的条码')

    def prepare_line_out_data(self, line_out_ids):
        line_data = {}
        for line in line_out_ids:
            line_data.update({line.goods_id.barcode: line})
        return line_data

    def contract_barcode_line_data(self, line_out_data, vals, code):
        line_out_list = []
        att = self.env['attribute'].search([('ean', '=', code)])
        goods = self.env['goods'].search([('barcode', '=', code)])
        if not att and not goods:
            return {'warning': {'title': u'警告', 'message': u'不存在条码为 %s 的商品' % code}}
        self.env['wh.move'].check_barcode(self._name, self.id, att, goods)
        conversion = att and att.goods_id.conversion or goods.conversion
        move, create_line, val = self.env['wh.move'].scan_barcode_each_model_operation(self._name, self.id, att,
                                                                                       goods,
                                                                                       conversion)
        if not line_out_data.get(code):
            if not create_line:
                line_out_list.append(
                    (0, 0, self.env['wh.move'].prepare_move_line_data(att, val, goods, move)))
        for currency_code, line in line_out_data.iteritems():
            if isinstance(line.id, int):
                if currency_code == code:
                    line_out_list.append((1, line.id,
                                          {'goods_qty': line.goods_qty + 1}))
                else:
                    line_out_list.append((4, line.id, False))
            else:
                currency_vals = {}
                for val in vals:
                    currency_vals.update({val: line[val]})
                if currency_code == code:
                    currency_vals.update({'goods_qty': line.goods_qty + 1})
                    line_out_list.append((0, 0, currency_vals))
                else:
                    line_out_list.append((0, 0, currency_vals))
        return line_out_list

    @api.multi
    @api.onchange('scan_barcode_input_code')
    def onchange_scan_barcode_input_code(self):
        vals = ['cost_unit', 'uos_id', 'goods_id', 'warehouse_dest_id', 'goods_uos_qty', 'warehouse_id', 'uom_id',
                'goods_qty', 'attribute_id', 'price_taxed', 'tax_rate', 'type', 'move_id']
        if self.scan_barcode_input_code:
            if ' ' in self.scan_barcode_input_code:
                code_list = self.scan_barcode_input_code.split(' ')
            else:
                code_list = [self.scan_barcode_input_code]
            for code in code_list:
                line_out_data = self.prepare_line_out_data(self.line_out_ids)
                line_out_list = self.contract_barcode_line_data(
                    line_out_data, vals, code)
                if isinstance(line_out_list, dict):
                    return line_out_list
                self.line_out_ids = line_out_list
        self.scan_barcode_input_code = u''
