# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016  开阖软件(<http://www.osbzr.com>).
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

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


PROVINCE_TYPE = [('cj_jy', u'上传城建，教育附加，地方教育附加'),
                      ('stamp_duty', u'印花税'),
                      ('social_security', u'社保'),
                      ('property', u'房产税')]

COUNTRY_TYPE = [('no1', u'运输服务'),
                 ('no2', u'电信服务'),
                 ('no3', u'建筑安装服务'),
                 ('no4', u'不动产租赁服务'),
                 ('no5', u'受让土地使用权'),
                 ('no6', u'金融保险服务'),
                 ('no7', u'生活服务'),
                 ('no8', u'取得无形资产'),
                 ('no10', u'货物及加工、修理修配劳务'),
                 ('no12', u'建筑安装服务'),
                 ('no14', u'购建不动产并一次性抵扣'),
                 ('no15', u'通行费'),
                 ('no16', u'有形动产租赁服务')]


class automatic_cost(models.Model):
    '''费用自动化基础'''
    _name = 'automatic.cost'
    _order = "name"

    name = fields.Char(u"关键字段")
    category_id = fields.Many2one('core.category', u'关联类别', help=u'用关键字段查找并关联类别', copy=False)
    account_in_id = fields.Many2one('finance.account', u'关联借方科目', copy=False, help=u'遇到会计科目不足时使用补充会计科目完成自动化记帐')
    account_out_id = fields.Many2one('finance.account', u'关联贷方科目', copy=False, help=u'遇到会计科目不足时使用补充会计科目完成自动化记帐')

class config_province(models.Model):
    _name = 'config.province'

    name = fields.Char(u'社会统一编码', required=True)
    balance_lins = fields.One2many('balance.line',
                               'order_id',
                               u'资产负债表',
                               copy=False,
                               required=True)
    profit_lins = fields.One2many('profit.line',
                               'order_id',
                               u'利润表',
                               copy=False,
                               required=True)

class balance_line(models.Model):
    _name = 'balance.line'

    order_id = fields.Many2one('config.province', u'单位名称', index=True,
                               required=True, ondelete='cascade')
    update_name = fields.Char(u'上传名称',
                          required=True)
    excel_ncows = fields.Char(u'EXCEL对应列',
                          required=True)
    excel_ncols = fields.Char(u'EXCEL对应行',
                             required=True)

class profit_lins(models.Model):
    _name = 'profit.line'

    order_id = fields.Many2one('config.province', u'单位名称', index=True,
                               required=True, ondelete='cascade')
    update_name = fields.Char(u'上传名称',
                          required=True)
    excel_ncows = fields.Char(u'EXCEL对应列',
                          required=True)
    excel_ncols = fields.Char(u'EXCEL对应行',
                             required=True)

class partner(models.Model):
    _inherit = 'partner'
    computer_import = fields.Boolean(u'系统创建',default= False)

class tax_base_category(models.Model):
    _name = 'tax.base.category'

    name = fields.Char(u'分类', help=u'对应ZZSTSGL')

class goods(models.Model):
    _inherit = 'goods'
    computer_import = fields.Boolean(u'系统创建',default= False)

class tax_category(models.Model):
    _name = 'tax.category'

    code = fields.Char(u'编号', required=True, help=u'对应SPBM')
    name = fields.Char(u'名称', required=True, help=u'对应SPMC')
    print_name = fields.Char(u'打印名称', help=u'对应SPBMJC')
    superior = fields.Many2one('tax.category', u'上级分类', help=u'上级类别', copy=False)
    can_use = fields.Boolean(u'可使用')
    base_category = fields.Many2one('tax.base.category', u'基础类别', help=u'对应ZZSTSGL', copy=False)
    note = fields.Text(u'备注')
    help = fields.Text(u'说明')
    tax_rate = fields.Char(u'税率', help='因为有可能有多个税率在这里面，所以现在很奇怪')

class CoreCategory(models.Model):
    _inherit = 'core.category'
    tax_category_id = fields.Many2one(
        'tax.category', string=u'税收分类')

class TaxConfigWizard(models.TransientModel):
    _name = 'tax.config.settings'
    _inherit = 'res.config.settings'
    _description = u'涉税会计默认设置'

    default_goods_supplier = fields.Many2one('core.category',u'默认商品供应商类别', help=u'选择新建默认供应商类别')
    default_service_supplier = fields.Many2one('core.category',u'默认服务供应商类别', help=u'选择新建默认服务供应商类别')
    default_customer = fields.Many2one('core.category',u'默认客户类别', help=u'选择新建默认供应商客户类别')
    default_buy_goods_account = fields.Many2one('finance.account',u'默认采购商品科目', help=u'选择新建默认购买商品类别')
    default_sell_goods_account = fields.Many2one('finance.account', u'默认销售商品科目', help=u'选择新建默认销售商品类别')

    default_tax_num = fields.Char(u'社会统一编码')
    default_country_name = fields.Char(u'地税登入名')
    default_country_password = fields.Char(u'地税密码')
    default_country_tel_number = fields.Char(u'手机后4位')
    default_company_name = fields.Char(u'企业名称')
    default_province_password = fields.Char(u'国税密码')
    default_dmpt_name = fields.Char(u'打码平台用户名')
    default_dmpt_password = fields.Char(u'打码平台密码')

    @api.multi
    def set_default_goods_supplier(self):
        res = self.env['ir.values'].sudo().set_default(
            'tax.config.settings', 'default_goods_supplier', self.default_goods_supplier.id)
        return res

    @api.multi
    def set_default_service_supplier(self):
        res = self.env['ir.values'].sudo().set_default(
            'tax.config.settings', 'default_service_supplier', self.default_service_supplier.id)
        return res

    @api.multi
    def set_default_customer(self):
        res = self.env['ir.values'].sudo().set_default(
            'tax.config.settings', 'default_customer', self.default_customer.id)
        return res

    @api.multi
    def set_default_buy_goods_account(self):
        res = self.env['ir.values'].sudo().set_default(
            'tax.config.settings', 'default_buy_goods_account', self.default_buy_goods_account.id)
        return res

    @api.multi
    def set_default_sell_goods_account(self):
        res = self.env['ir.values'].sudo().set_default(
            'tax.config.settings', 'default_sell_goods_account', self.default_sell_goods_account.id)
        return res

    @api.multi
    def set_default_tax_num(self):
        res = self.env['ir.values'].sudo().set_default(
            'tax.config.settings', 'default_tax_num', self.default_tax_num)
        return res

    @api.multi
    def set_default_country_name(self):
        res = self.env['ir.values'].set_default(
            'tax.config.settings', 'default_country_name', self.default_country_name)
        return res

    @api.multi
    def set_default_country_tel_number(self):
        res = self.env['ir.values'].set_default(
            'tax.config.settings', 'default_country_tel_number', self.default_country_tel_number)
        return res

    @api.multi
    def set_default_company_name(self):
        res = self.env['ir.values'].set_default(
            'tax.config.settings', 'default_company_name', self.default_company_name)
        return res

    @api.multi
    def set_default_province_password(self):
        res = self.env['ir.values'].set_default(
            'tax.config.settings', 'default_province_password', self.default_province_password)
        return res

    @api.multi
    def set_default_country_password(self):
        res = self.env['ir.values'].set_default(
            'tax.config.settings', 'default_country_password', self.default_country_password)
        return res

    @api.multi
    def set_default_dmpt_name(self):
        res = self.env['ir.values'].set_default(
            'tax.config.settings', 'default_dmpt_name', self.default_dmpt_name)
        return res

    @api.multi
    def set_default_dmpt_password(self):
        res = self.env['ir.values'].set_default(
            'tax.config.settings', 'default_dmpt_password', self.default_dmpt_password)
        return res