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

    @api.multi
    def button_ok(self):
        res = []
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        cond = [('date', '>=', self.date_start),
                ('date', '<=', self.date_end)]
        if self.goods_id:
            cond.append(('goods', '=', self.goods_id.name))
        if self.partner_id:
            cond.append(('partner', '=', self.partner_id.name))

        view = self.env.ref('buy.buy_summary_partner_tree')
        return {
            'name': u'采购汇总表（按供应商）',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'res_model': 'buy.summary.partner',
            'type': 'ir.actions.act_window',
            'domain': cond,
            'limit': 300,
        }
