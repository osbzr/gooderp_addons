# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  德清武康开源软件().
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
import xlrd
import base64
import datetime
import time
import random


# 字段只读状态
READONLY_STATES = {
        'done': [('readonly', True)],
    }

#每月销售发票
class tax_invoice_out(models.Model):
    _name = 'tax.invoice.out'
    _order = "name"
    name = fields.Many2one(
        'finance.period',
        u'会计期间',
        ondelete='restrict',
        required=True,
        states=READONLY_STATES)
    line_ids = fields.One2many('cn.account.invoice', 'invoice_out_id', u'销售发票明细',
                               states=READONLY_STATES, copy=False)
    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已结束')], u'状态', default='draft')
    total_tax = fields.Float(string=u'合计销项税额', store=True, readonly=True,
                        compute='_compute_tax', track_visibility='always',
                        digits=dp.get_precision('Amount'))
    total_amount = fields.Float(string=u'合计销售金额', store=True, readonly=True,
                             compute='_compute_amount', track_visibility='always',
                             digits=dp.get_precision('Amount'))

    @api.multi
    def invoice_to_sell(self):
        '''反推订单'''
        for invoice in self.line_ids:
            invoice.create_uom()
            invoice.create_category()
            invoice.create_product()
            invoice.create_sell_partner()
            invoice.to_sell()
        return True

    @api.multi
    def tax_invoice_draft(self):
        for rec in self:
            if rec.state == 'draft':
                raise UserError(u'请不要重复反确认')
            rec.state = 'draft'

    @api.multi
    def tax_invoice_done(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(u'请不要重复确认')
            for line in rec.line_ids:
                if not line.sell_id:
                    raise UserError(u'发票号码：%s未下推生成销售订单！'%line.name)
            rec.state = 'done'

    #引入EXCEL的wizard的button
    @api.multi
    def button_excel(self):
        return {
            'name': u'引入excel',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'create.sale.invoice.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

#增加按月进项发票
class cn_account_invoice(models.Model):
    _inherit = 'cn.account.invoice'
    _description = u'中国发票'
    _rec_name='name'

    invoice_out_id = fields.Many2one('tax.invoice.out', u'对应入帐月份', index=True, copy=False, readonly=True)
    sell_id = fields.Many2one('sell.order', u'销售订单号', copy=False, readonly=True,
                             ondelete='cascade',
                             help=u'产生的销售订单')

    @api.multi
    def to_sell(self):
        # 系统创建的客户或产品不能审核
        partner_id = self.env['partner'].search([
            ('name', '=', self.partner_name_out)])
        # if partner_id.computer_import:
        #     raise UserError(u'系统创建的客户不能审核！')
        # 随机取0-15中整数，让订单日期在发票日期前15-30天内变化
        date = datetime.datetime.strptime(self.invoice_date, '%Y-%m-%d') - datetime.timedelta(
            days=random.randint(0, 15) + 15)
        sell_id = self.env['sell.order'].create({
            'partner_id': partner_id.id,
            'date': date,
            'delivery_date': self.invoice_date,
            'warehouse_id': self.env['warehouse'].search([('type', '=', 'stock')], limit=1).id,
        })
        for line in self.line_ids:
            goods_id = self.env['goods'].search([('name', '=', line.product_name)], limit=1)
            uom_id = self.env['uom'].search([('name', '=', line.product_unit)], limit=1)
            # if goods_id.computer_import:
            #     raise UserError(u'系统创建的产品不能审核！')
            self.env['sell.order.line'].create({
                'goods_id': goods_id.id,
                'order_id': sell_id.id,
                'uom_id': uom_id.id,
                'quantity': line.product_count,
                'price': line.product_amount / line.product_count,
                'price_taxed': (line.product_amount + line.product_tax) / line.product_count,
                'amount': line.product_amount,
                'tax_rate': round(line.product_tax / line.product_amount * 100, 0),
                'tax_amount': line.product_tax,
            })
        self.sell_id = sell_id.id
        sell_id.sell_order_done()
        delivery_id = self.env['sell.delivery'].search([
            ('order_id', '=', sell_id.id)])
        delivery_id.sell_delivery_done()



#导入金穗发票，生成销售发票及明细
class create_sale_invoice_wizard(models.TransientModel):
    _name = 'create.sale.invoice.wizard'
    _description = 'Sale Invoice Import'

    excel = fields.Binary(u'导入金穗系统导出的excel文件',)

    @api.one
    def create_sale_invoice(self):
        """
        通过Excel文件导入信息到tax.invoice
        """
        invoice_out = self.env['tax.invoice.out'].browse(self.env.context.get('active_id'))
        if not invoice_out:
            return {}
        xls_data = xlrd.open_workbook(
                file_contents=base64.decodestring(self.excel))
        table = xls_data.sheets()[0]
        #取得行数
        ncows = table.nrows
        #取得第6行数据
        colnames =  table.row_values(5)
        list =[]
        newcows = 0
        for rownum in range(6,ncows):
            row = table.row_values(rownum)
            if row:
                app = {}
                for i in range(len(colnames)):
                   app[colnames[i]] = row[i]
                if app.get(u'金额') and app.get(u'金额')!=u'金额':
                    list.append(app)
                    newcows += 1
        #数据读入。
        for data in range(0,newcows):
            in_xls_data = list[data]
            invoice_code = in_xls_data.get(u'发票代码')
            partner_name = in_xls_data.get(u'购方企业名称')
            goods = in_xls_data.get(u'商品名称')
            product_type = in_xls_data.get(u'规格')
            product_unit = in_xls_data.get(u'单位')
            product_count = in_xls_data.get(u'数量')
            product_price = in_xls_data.get(u'单价')
            product_amount = float(in_xls_data.get(u'金额'))
            product_tax_rate = float(in_xls_data.get(u'税率') != '' and in_xls_data.get(u'税率')[:-1])
            product_tax = float(in_xls_data.get(u'税额'))
            have_type = goods.split('*')
            if len(have_type) > 1:
                goods_name = goods.split('*')[-1]
                tax_type = goods.split('*')[1]
            else:
                goods_name = goods
                tax_type = ''
            if invoice_code and invoice_code[7] == '3' and invoice_code[9] == '0':
                invoice_type = 'pt'
            else:
                invoice_type = 'zy'
            #创建销售发票
            if in_xls_data.get(u'购方税号'):
                invoice_id = self.env['cn.account.invoice'].create({
                    'type': 'out',
                    'partner_name_out': partner_name,
                    'partner_code_out': str(in_xls_data.get(u'购方税号')),
                    'partner_address_out': in_xls_data.get(u'地址电话'),
                    'partner_bank_number_out': in_xls_data.get(u'银行账号'),
                    'invoice_code': invoice_code,
                    'name': str(in_xls_data.get(u'发票号码')),
                    'invoice_date': self.excel_date(in_xls_data.get(u'开票日期')),
                    'invoice_type': invoice_type,
                    'is_verified': True,
                    'invoice_amount': product_amount,
                    'invoice_tax': product_tax,
                    'invoice_out_id': invoice_out.id or '',
                })
            if in_xls_data.get(u'商品名称') and in_xls_data.get(u'商品名称') == u'小计':
                invoice_id.write({'invoice_amount': product_amount,'invoice_tax':product_tax})
                continue
            if in_xls_data.get(u'商品名称') and in_xls_data.get(u'商品名称') != u'小计':
                self.env['cn.account.invoice.line'].create({
                    'order_id': invoice_id.id,
                    'product_name': goods_name or '',
                    'product_type': product_type or '',
                    'product_unit': product_unit or '',
                    'product_count': product_count or '',
                    'product_price': product_price or '',
                    'product_amount': product_amount or '0',
                    'product_tax_rate': product_tax_rate,
                    'product_tax': product_tax or '0',
                    'tax_type': tax_type or '',
                    })


    def excel_date(self,data):
        #将excel日期改为正常日期
        if type(data) in (int,float):
            year, month, day, hour, minute, second = xlrd.xldate_as_tuple(data,0)
            py_date = datetime.datetime(year, month, day, hour, minute, second)
        else:
            py_date = data
        return py_date