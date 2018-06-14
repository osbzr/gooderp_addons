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

#每月进项发票
class tax_invoice_in(models.Model):
    _name = 'tax.invoice.in'
    _order = "name"
    name = fields.Many2one(
        'finance.period',
        u'会计期间',
        ondelete='restrict',
        required=True,
        states=READONLY_STATES)
    line_ids = fields.One2many('cn.account.invoice', 'invoice_in_id', u'进项发票明细行',
                               states=READONLY_STATES, copy=False)
    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已结束')], u'状态', default='draft')
    tax_amount = fields.Float(string=u'合计可抵扣税额', store=True, readonly=True,
                        compute='_compute_tax_amount', track_visibility='always',
                        digits=dp.get_precision('Amount'))

    @api.one
    @api.depends('line_ids.invoice_tax', 'line_ids.is_deductible')
    def _compute_tax_amount(self):
        '''当明细行的税额或是否抵扣改变时，改变可抵扣税额合计'''
        total = 0
        for line in self.line_ids:
            if line.is_deductible:
                total += 0
            else:
                total = total + line.invoice_tax
        self.tax_amount = total

    #由发票生成采购订单
    @api.one
    def invoice_to_buy(self):
        for invoice in self.line_ids:
            invoice.create_uom()
            invoice.create_category()
            invoice.create_product()
            invoice.create_buy_partner()
            invoice.to_buy()
        return True

    #引入EXCEL的wizard的button
    @api.multi
    def button_excel(self):
        return {
            'name': u'引入excel',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'create.cn.account.invoice.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def write(self, vals):
        res = super(tax_invoice_in, self).write(vals)
        return res

    @api.one
    @api.multi
    def tax_invoice_draft(self):
        self.state = 'draft'

    @api.one
    @api.multi
    def tax_invoice_done(self):
        for line in self.line_ids:
            if not line.buy_id:
                raise UserError(u'发票号码：%s未下推生成采购订单！' % line.name)
        self.state = 'done'


#用excel导入认证系统的EXCEL生成月认证发票
class create_cn_account_invoice_wizard(models.TransientModel):
    _name = 'create.cn.account.invoice.wizard'
    _description = 'Tax Invoice Import'

    excel = fields.Binary(u'导入认证系统导出的excel文件',)

    def create_cn_account_invoice(self):
        if not self.env.context.get('active_id'):
            return
        invoice_in = self.env['tax.invoice.in'].browse(self.env.context.get('active_id'))
        """
        通过Excel文件导入信息到cn.account.invoice
        """
        if not invoice_in:
            return {}
        xls_data = xlrd.open_workbook(file_contents=base64.decodestring(self.excel))
        table = xls_data.sheets()[0]
        ncows = table.nrows
        ncols = 0
        colnames = table.row_values(0)
        list =[]
        #数据读入，过滤没有开票日期的行
        for rownum in range(1,ncows):
            row = table.row_values(rownum)
            if row:
                app = {}
                for i in range(len(colnames)):
                   app[colnames[i]] = row[i]
                if app.get(u'开票日期'):
                    list.append(app)
                    ncols += 1

        #数据处理
        in_xls_data = {}
        for data in range(0,ncols):
            in_xls_data = list[data]
            invoice_code = in_xls_data.get(u'发票代码')
            partner_name = in_xls_data.get(u'销方名称')
            self.env['cn.account.invoice'].create({
                'type': 'in',
                'partner_name_in': partner_name,
                'partner_code_in': str(in_xls_data.get(u'销方税号')),
                'invoice_code': str(invoice_code),
                'name': str(in_xls_data.get(u'发票号码')),
                'invoice_amount': float(in_xls_data.get(u'金额')),
                'invoice_tax': float(in_xls_data.get(u'税额')),
                'invoice_date': self.excel_date(in_xls_data.get(u'开票日期')),
                'invoice_confirm_date': self.excel_date(in_xls_data.get(u'认证时间') or in_xls_data.get(u'确认时间')),
                'invoice_type': 'zy',
                'invoice_in_id': invoice_in.id or '',
                'tax_rate': float(in_xls_data.get(u'税额'))/float(in_xls_data.get(u'金额'))*100,
                'is_verified': False,
                })

    def excel_date(self,data):
        #将excel日期改为正常日期
        if type(data) in (int,float):
            year, month, day, hour, minute, second = xlrd.xldate_as_tuple(data,0)
            py_date = datetime.datetime(year, month, day, hour, minute, second)
        else:
            py_date = data
        return py_date

#增加按月进项发票
class cn_account_invoice(models.Model):
    _inherit = 'cn.account.invoice'
    _description = u'中国发票'
    _rec_name='name'

    invoice_in_id = fields.Many2one('tax.invoice.in', u'对应入帐月份', index=True, copy=False, readonly=True)
    buy_id = fields.Many2one('buy.order', u'采购订单号', copy=False, readonly=True,
                             ondelete='cascade',
                             help=u'产生的采购订单')

    @api.multi
    def to_buy(self):
        ''' 系统创建的客户或产品不能审核'''
        buy_partner_id = self.env['partner'].search([('name', '=', self.partner_name_in)])
        # if buy_partner_id.computer_import:
        #     raise UserError(u'系统创建的客户不能审核！')
        for line in self.line_ids:
            goods_id = self.env['goods'].search([('name', '=', line.product_name)])
            # if goods_id.computer_import:
            #     raise UserError(u'系统创建的产品不能审核！')

        # 随机取0-15中整数，让订单日期在发票日期前20-35天内变化
        date = datetime.datetime.strptime(self.invoice_date, '%Y-%m-%d') - datetime.timedelta(
            days=random.randint(0, 15) + 20)
        buy_id = self.env['buy.order'].create({
            'partner_id': buy_partner_id.id,
            'date': date,
            'planned_date': self.invoice_confirm_date,
            'warehouse_dest_id': self.env['warehouse'].search([('type', '=', 'stock')], limit=1).id,
        })
        if self.line_ids:
            for line in self.line_ids:
                goods_id = self.env['goods'].search([('name', '=', line.product_name)])
                self.env['buy.order.line'].create({
                    'goods_id': goods_id.id,
                    'order_id': buy_id.id,
                    'uom_id': goods_id.uom_id.id,
                    'quantity': line.product_count,
                    'price': line.product_price,
                    'price_taxed': round(line.product_price * (1 + line.product_tax_rate / 100), 2),
                    'amount': line.product_amount,
                    'tax_rate': line.product_tax_rate,
                    'tax_amount': line.product_tax,
                })
            self.buy_id = buy_id
            buy_id.buy_order_done()
            delivery_id  = self.env['buy.receipt'].search([
                ('order_id', '=', buy_id.id)])
            delivery_id.buy_receipt_done()
            invoice_id = self.env['money.invoice'].search([
                ('name', '=', delivery_id.name)])
            invoice_id.bill_number = self.name