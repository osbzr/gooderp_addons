# -*- coding: utf-8 -*-

from datetime import date
from openerp import models, fields, api
from openerp.exceptions import except_orm


class sell_summary_goods_wizard(models.TransientModel):
    _name = 'sell.summary.goods.wizard'
    _description = u'销售汇总表（按商品）向导'

    @api.model
    def _default_date_start(self):
        return self.env.user.company_id.start_date

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(u'开始日期', default=_default_date_start)
    date_end = fields.Date(u'结束日期', default=_default_date_end)
    partner_id = fields.Many2one('partner', u'客户')
    goods_id = fields.Many2one('goods', u'商品')
    goods_categ_id = fields.Many2one('core.cetegory', u'商品类别')

    @api.multi
    def button_ok(self):
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        return {
            'name': u'销售汇总表（按商品）',
            'view_mode': 'tree',
            'res_model': 'sell.summary.goods',
            'type': 'ir.actions.act_window',
            'context': self.read(['date_start', 'date_end', 'partner_id', 'goods_id', 'goods_categ_id'])[0],
        }
