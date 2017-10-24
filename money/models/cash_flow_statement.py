# -*- coding: utf-8 -*-
##############################################################################
import odoo.addons.decimal_precision as dp
from odoo import fields, models, api

LINE_TYPES = [('get', u'销售收款'),
              ('pay', u'采购付款'),
              ('category', u'其他收支'),
              ('begin', u'科目期初'),
              ('end', u'科目期末'),
              ('lines', u'表行计算')]


class CashFlowTemplate(models.Model):
    _name = 'cash.flow.template'
    _order = 'sequence'

    sequence = fields.Integer(u'序号')
    name = fields.Char(u'项目')
    line_num = fields.Char(u'行次')
    line_type = fields.Selection(LINE_TYPES, u'行类型')
    # for type sum
    category_ids = fields.Many2many(
        'core.category', string=u'收支类别', domain="[('type','in',['other_get','other_pay'])]")
    # for type begin
    begin_ids = fields.Many2many('finance.account', string=u'会计科目期初')
    # for type end
    end_ids = fields.Many2many('finance.account', string=u'会计科目期末')
    # for type lines
    plus_ids = fields.Many2many(
        'cash.flow.template', 'c_p', 'c_id', 'p_id', string=u'+表行')
    nega_ids = fields.Many2many(
        'cash.flow.template', 'c_n', 'c_id', 'n_id', string=u'-表行')


class CashFlowStatement(models.Model):
    _name = 'cash.flow.statement'
    name = fields.Char(u'项目')
    line_num = fields.Char(u'行次')
    amount = fields.Float(u'本月金额', digits=dp.get_precision('Amount'))
    year_amount = fields.Float(u'本年累计金额', digits=dp.get_precision('Amount'))


class CoreCategory(models.Model):
    _inherit = 'core.category'
    cash_flow_template_ids = fields.Many2many(
        'cash.flow.template', string=u'现金流量表行')
