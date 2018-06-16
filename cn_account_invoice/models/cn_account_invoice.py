# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  德清武康开源软件().
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundaption, either version 3 of the
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
import odoo.addons.decimal_precision as dp
import datetime
import random
from odoo.exceptions import UserError


#定意发票todo add confirm_month
class cn_account_invoice(models.Model):
    _name = 'cn.account.invoice'
    _description = u'中国发票'
    _rec_name='name'

    partner_name_in = fields.Char(u'供应商名称', copy=False)
    partner_code_in = fields.Char(u'供应商税号', copy=False)
    partner_address_in = fields.Char(u'供应商地址及电话', copy=False)
    partner_bank_number_in = fields.Char(u'供应商银行及帐号', copy=False)
    partner_name_out = fields.Char(u'客户名称', copy=False)
    partner_code_out = fields.Char(u'客户税号', copy=False)
    partner_address_out = fields.Char(u'客户地址及电话', copy=False)
    partner_bank_number_out = fields.Char(u'客户银行及帐号', copy=False)
    type = fields.Selection([('in', u'进项发票'),
                              ('out', u'销项发票')], u'进/出发票', copy=False)
    invoice_type = fields.Selection([('pt', u'增值税普通发票'),
                              ('zy', u'增值税专用发票'),
                              ('dz',u'电子普通发票'),
                              ('other',u'其他发票')], u'发票类型', copy=False)
    invoice_code = fields.Char(u'发票代码', copy=False)
    name = fields.Char(u'发票号码', copy=False)
    invoice_amount = fields.Float(u'金额', copy=False)
    invoice_tax = fields.Float(u'税额', copy=False)
    invoice_heck_code = fields.Char(u"发票校验码", copy=False)
    invoice_date = fields.Date(u'开票日期', copy=False)
    invoice_confirm_date = fields.Date(u'认证日期', copy=False)
    tax_rate = fields.Float(u'税率',digits=(12, 0),copy=False)
    is_deductible = fields.Boolean(u'是否抵扣')
    is_verified = fields.Boolean(u'已核验')
    line_ids=fields.One2many('cn.account.invoice.line', 'order_id', u'发票明细行',
                               copy=False)
    attachment_number = fields.Integer(compute='_compute_attachment_number', string=u'附件号')
    note = fields.Text(u"备注")

    _sql_constraints = [
        ('unique_invoice_code_name', 'unique (invoice_code, name)', u'发票代码+发票号码不能相同!'),
    ]

    @api.multi
    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'cn.account.invoice'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'cn.account.invoice', 'default_res_id': self.id}
        return res

    @api.multi
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'cn.account.invoice'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    @api.multi
    def create_uom(self):
        for mx in self.line_ids:
            uom = mx.product_unit
            if uom:
                uom_id = self.env['uom'].search([('name', '=', uom)])
                if not uom_id:
                    uom_id = self.env['uom'].create({
                        'name': uom,
                        'active': 1})

    @api.multi
    def create_category(self):
        for mx in self.line_ids:
            category = mx.tax_type
            if category:
                category_id = self.env['core.category'].search([
                    '&', ('type', '=', 'goods'), ('tax_category_id.print_name', '=', category)])
                if not category_id:
                    if self.type == 'in':
                        account_id = self.env['ir.values'].get_default('tax.config.settings', 'default_buy_goods_account')
                    if self.type == 'out':
                        account_id = self.env['ir.values'].get_default('tax.config.settings',
                                                                       'default_sell_goods_account')
                    category_id = self.env['core.category'].create({
                        'type': 'goods',
                        'name': category,
                        'account_id': account_id,
                        'tax_category_id': self.env['tax.category'].search([('print_name', '=', category)],limit=1).id,
                        'note': u'由系统自动增加'
                    })

    @api.multi
    def create_product(self):
        for mx in self.line_ids:
            goods = mx.product_name
            uom = mx.product_unit
            uom_id = self.env['uom'].search([('name', '=', uom)])
            category = mx.tax_type
            category_id = self.env['core.category'].search([
                '&', ('type', '=', 'goods'), ('tax_category_id.print_name', '=', category)])
            if category_id and category_id.tax_category_id.code[0] == '1':
                no_stock = False
            else:
                no_stock = True

            if goods:
                goods_id = self.env['goods'].search([('name', '=', goods)])
                if not goods_id:
                    self.env['goods'].create({
                        'name': goods,
                        'uom_id': uom_id and uom_id.id,
                        'uos_id': uom_id and uom_id.id,
                        # 'tax_rate': float(in_xls_data.get(u'税率')),
                        'category_id': category_id and category_id.id,
                        'computer_import': True,
                        'no_stock': no_stock,
                        'cost_method': 'average',
                    })

    # 创建供应商
    @api.multi
    def create_buy_partner(self):
        if self.partner_code_in:
            partner_id = self.env['partner'].search([
                ('tax_num', '=', self.partner_code_in)])
        if self.partner_name_in:
            partner_id = self.env['partner'].search([
                ('name', '=', self.partner_name_in)])
        default_goods_supplier = self.env['ir.values'].get_default('tax.config.settings', 'default_goods_supplier')
        if not default_goods_supplier:
            raise UserError(u'请设置默认供应商类别！')
        if not partner_id:
            partner_id = self.env['partner'].create({
                'name': self.partner_name_in,
                'main_mobile': self.partner_code_in,
                'tax_num': self.partner_code_in,
                's_category_id': default_goods_supplier,
                'computer_import': True,
            })
        # 补银行帐号等信息
        if self.partner_address_in and partner_id.main_mobile == partner_id.tax_num:
            main_mobile = self.split_number(self.partner_address_in)
            partner_id.write({'main_mobile': main_mobile})
        if self.partner_address_in and not partner_id.main_address:
            if partner_id.main_mobile and partner_id.main_mobile != partner_id.tax_num:
                to_del_mobile = len(partner_id.main_mobile)
            else:
                to_del_mobile = 0
            main_address = self.partner_address_in[:-to_del_mobile]
            partner_id.write({'main_address': main_address})
        if self.partner_bank_number_in and not partner_id.bank_num:
            bank_number = self.split_number(self.partner_bank_number_in)
            partner_id.write({'bank_num': bank_number})
        if self.partner_bank_number_in and not (partner_id.bank_num or partner_id.bank_name):
            if partner_id.bank_num:
                to_del_bank_number = len(partner_id.bank_num)
            else:
                to_del_bank_number = 0
            bank_name = self.partner_bank_number_in[:-to_del_bank_number]
            partner_id.write({'bank_name': bank_name})

    # 创建客户
    @api.multi
    def create_sell_partner(self):
        if self.partner_code_out:
            partner_id = self.env['partner'].search([
                ('tax_num', '=', self.partner_code_out)])
        elif self.partner_name_out:
            partner_id = self.env['partner'].search([
                ('name', '=', self.partner_name_out)])
        default_customer = self.env['ir.values'].get_default('tax.config.settings', 'default_customer')
        if not default_customer:
            raise UserError(u'请设置默认客户类别！')
        if not partner_id:
            partner_id = self.env['partner'].create({
                'name': self.partner_name_out,
                'main_mobile': self.partner_code_out,
                'tax_num': self.partner_code_out,
                'c_category_id':default_customer,
                'computer_import': True,
            })
        # 补银行帐号等信息
        if self.partner_address_out and partner_id.main_mobile == partner_id.tax_num:
            main_mobile = self.split_number(self.partner_address_out)
            partner_id.write({'main_mobile': main_mobile})
        if self.partner_address_out and not partner_id.main_address:
            if partner_id.main_mobile and partner_id.main_mobile != partner_id.tax_num:
                to_del_mobile = len(partner_id.main_mobile)
            else:
                to_del_mobile = 0
            main_address = self.partner_address_out[:-to_del_mobile]
            partner_id.write({'main_address': main_address})
        if self.partner_bank_number_out and not partner_id.bank_num:
            bank_number = self.split_number(self.partner_bank_number_out)
            partner_id.write({'bank_num': bank_number})
        if self.partner_bank_number_out and not partner_id.bank_name:
            if partner_id.bank_num:
                to_del_bank_number = len(partner_id.bank_num)
            else:
                to_del_bank_number = 0
            bank_name = self.partner_bank_number_out[:-to_del_bank_number]
            partner_id.write({'bank_name': bank_name})

    # 跟据帐号和电话都在后面的特性，使用倒转后从头直至有字母出现为此都是帐号和电话。
    def split_number(self, str):
        str1 = str[::-1]  #
        changdu = len(str1)  # 取长度
        num = ''
        i = 0
        while i < changdu:
            if str1[i].isdigit() or str1[i] == '-' or str1[i] == ' ':
                num += str1[i]
                i += 1
            else:
                return num[::-1]

#定义发票明细行
class cn_account_invoice_line(models.Model):
    _name = 'cn.account.invoice.line'
    _description = u'中国发票明细'
    _rec_name='product_name'

    order_id = fields.Many2one('cn_account_invoice', u'发票',help=u'关联发票',copy=False)
    product_name = fields.Char(u"货物名称",copy=False)
    product_type = fields.Char(u"规格型号",copy=False)
    product_unit = fields.Char(u"单位",copy=False)
    product_count = fields.Float(u"数量",copy=False)
    product_price = fields.Float(u"价格",copy=False)
    product_amount = fields.Float(u"金额",copy=False)
    product_tax_rate = fields.Float(u"税率",copy=False)
    product_tax = fields.Float(u"税额",copy=False)
    tax_type = fields.Char(u'税收分类编码',help=u'20170101以后使用的税收分类编码，这个很重要',copy=False)