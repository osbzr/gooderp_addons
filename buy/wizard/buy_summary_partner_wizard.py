# -*- coding: utf-8 -*-

from datetime import date
from openerp import models, fields, api
from openerp.exceptions import except_orm


class buy_summary_partner_wizard(models.TransientModel):
    _name = 'buy.summary.partner.wizard'
    _description = u'采购汇总表（按供应商）向导'

    @api.model
    def _default_date_start(self):
        return self.env.user.company_id.start_date

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(u'开始日期', default=_default_date_start)
    date_end = fields.Date(u'结束日期', default=_default_date_end)
    partner_id = fields.Many2one('partner', u'供应商')
    goods_id = fields.Many2one('goods', u'产品')
    s_category_id = fields.Many2one('core.category', u'供应商类别')

    @api.multi
    def button_ok(self):
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')
        read_fields = ['date_start', 'date_end', 'partner_id', 'goods_id', 's_category_id']
        return {
            'name': u'采购汇总表（按供应商）',
            'view_mode': 'tree',
            'res_model': 'buy.summary.partner',
            'type': 'ir.actions.act_window',
            'context': self.read(read_fields)[0],
        }
