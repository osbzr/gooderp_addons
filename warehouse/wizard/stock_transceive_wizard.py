# -*- coding: utf-8 -*-

from datetime import date, timedelta
from odoo import models, fields, api


class ReportStockTransceiveWizard(models.TransientModel):
    _name = 'report.stock.transceive.wizard'
    _description = u'商品收发明细表向导'

    @api.model
    def _default_date_start(self):
        return date.today().replace(day=1).strftime('%Y-%m-%d')

    @api.model
    def _default_date_end(self):
        now = date.today()
        next_month = now.month == 12 and now.replace(year=now.year + 1,
                                                     month=1, day=1) or now.replace(month=now.month + 1, day=1)

        return (next_month - timedelta(days=1)).strftime('%Y-%m-%d')

    date_start = fields.Date(u'开始日期', default=_default_date_start,
                             help=u'查看本次报表的开始日期')
    date_end = fields.Date(u'结束日期', default=_default_date_end,
                           help=u'查看本次报表的结束日期')
    warehouse_id = fields.Many2one('warehouse', u'仓库',
                                   help=u'本次报表查看的仓库')
    goods_id = fields.Many2one('goods', u'商品',
                               help=u'本次报表查看的商品')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.onchange('date_start', 'date_end')
    def onchange_date(self):
        if self.date_start and self.date_end and self.date_end < self.date_start:
            return {'warning': {
                'title': u'错误',
                'message': u'结束日期不可以小于开始日期'
            }, 'value': {'date_end': self.date_start}}

        return {}

    @api.multi
    def open_report(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'report.stock.transceive',
            'view_mode': 'tree',
            'name': u'商品收发明细表 %s 至  %s ' % (self.date_start, self.date_end),
            'context': self.read(['date_start', 'date_end', 'warehouse_id', 'goods_id'])[0],
            'limit': 65535,
        }
