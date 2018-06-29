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
import urllib
import httplib2
import re
from lxml import etree


currency_code = {'GBP': '1314',
                 'HKD': '1315',
                 'USD': '1316',
                 'DEM': '1318',
                 'CHF': '1319',
                 'SGD': '1375',
                 'SKr': '1320',
                 'DKr': '1321',
                 'NKr': '1322',
                 'JPY': '1323',
                 'CAD': '1324',
                 'AUD': '1325',
                 'EUR': '1326',
                 'PHP': '1328',
                 'NZD': '1330',
                 'KRW': '1331',
                 'RBL': '1843',
                 'MYR': '2890',
                 'NTD': '2895',
                 'ESP': '1370',
                 'ITL': '1371',
                 'NLG': '1372',
                 'BEF': '1373',
                 'FIM': '1374',
                 'IDR': '3030',
                 'BRL': '3253', }


class Currency(models.Model):
    _inherit = 'res.currency'

    month_exchange = fields.One2many(
        'auto.exchange.line', 'currency_id', u'期间汇率', copy=False)

    @api.multi
    def get_web_exchange(self, line_date):
        '''用爬虫的方法取得中国银行汇率'''
        http = httplib2.Http()
        if self.name not in currency_code:
            raise UserError(u'中国银行找不到您的(%s)币别汇率' % self.name)
        url = 'http://srh.bankofchina.com/search/whpj/search.jsp'
        body = {
            'erectDate': line_date,
            'nothing': line_date,
            'pjname': currency_code[self.name]
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.6 Safari/537.36',
            'Content-type': 'application/x-www-form-urlencoded'
        }
        try:
            response, content = http.request(
                url, 'POST', headers=headers, body=urllib.urlencode(body))
            result = etree.HTML(content.decode('utf8')).xpath(
                '//table[@cellpadding="0"]/tr[4]/td/text()')
        except httplib2.HttpLib2Error:  # pragma: no cover
            raise UserError(u'网页设置有误(%s)请联系作者：（qq：2201864）' % url)
        return result[5]

    @api.multi
    def get_exchange(self):
        '''当设置自动运行时，传来的self为空值，需要补全所需自动运行的那几个ids'''
        if not self:
            currency_ids = self.env['res.currency'].search(
                [('active', '=', True)])
        else:
            currency_ids = self
        for currency in currency_ids:
            for line in currency.month_exchange:
                '''判断当前日期能不能取到汇率，如发现已有汇率则不重复取,取得的为100人民币汇率，需要／100'''
                self = currency
                if line.date <= fields.Date.context_today(self) and not line.exchange:
                    line_date = line.date
                    line.exchange = float(
                        self.get_web_exchange(line_date)) / 100
                    line.note = u'系统于(%s)从中国银行网站上取得' % fields.Date.context_today(
                        self)

    '''取汇率函数，如果要给定日期，需要在context里增加date'''
    @api.multi
    def _compute_current_rate(self):
        date = self._context.get('date') or fields.Datetime.now()
        period_id = self.env['finance.period'].get_period(date).id
        for currency in self:
            currency.rate = 1.0
            for line in currency.month_exchange:
                if period_id == line.period_id.id:
                    currency.rate = line.exchange or 1.0


class AutoExchangeLine(models.Model):
    _name = 'auto.exchange.line'
    _description = u'自动汇率明细行'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    date = fields.Date(u'抓取日期',
                       index=True, copy=False, help=u"应为每个月的第一个工作日")
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    exchange = fields.Float(u'外管局中间价', digits=(12, 4),
                            help=u'取得的汇率')
    note = fields.Char(u'备注',
                       help=u'本行备注')
    currency_id = fields.Many2one('res.currency', u'币别', index=True,
                                  required=True, ondelete='cascade',
                                  help=u'关联订单的编号')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    _sql_constraints = [
        ('unique_start_date', 'unique (currency_id,period_id)', u'同币别期间不能重合!'),
    ]


class CurrencyMoneyOrder(models.Model):
    _inherit = 'money.order'

    @api.multi
    def get_rate_silent(self, date, currency_id):
        currency = self.env['res.currency'].search([('id', '=', currency_id)])
        period_id = self.env['finance.period'].get_period(date)
        for line in currency.month_exchange:
            if period_id == line.period_id:
                rate = line.exchange
        if not rate:
            raise UserError(u'没有设置会计期间内的外币%s汇率' % currency.name)

        return rate
