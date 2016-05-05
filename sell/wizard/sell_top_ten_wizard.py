# -*- coding: utf-8 -*-

from datetime import date, timedelta
from openerp import models, fields, api
from openerp.exceptions import except_orm


class sell_top_ten_wizard(models.TransientModel):
    _name = 'sell.top.ten.wizard'
    _description = u'销量前十商品向导'

    @api.model
    def _default_date_start(self):
        '''返回6天前的日期'''
        now = date.today()
        return (now - timedelta(days=6)).strftime('%Y-%m-%d')

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(u'开始日期', default=_default_date_start)
    date_end = fields.Date(u'结束日期', default=_default_date_end)

    @api.multi
    def button_ok(self):
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        return {
            'name': u'销量前十商品',
            'view_mode': 'tree',
            'res_model': 'sell.top.ten',
            'type': 'ir.actions.act_window',
            'context': self.read(['date_start', 'date_end'])[0],
        }
