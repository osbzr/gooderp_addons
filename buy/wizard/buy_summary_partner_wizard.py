
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class BuySummaryPartnerWizard(models.TransientModel):
    _name = 'buy.summary.partner.wizard'
    _description = '采购汇总表（按供应商）向导'

    @api.model
    def _default_date_start(self):
        return self.env.user.company_id.start_date

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date('开始日期', default=_default_date_start,
                             help='报表汇总的开始日期，默认为公司启用日期')
    date_end = fields.Date('结束日期', default=_default_date_end,
                           help='报表汇总的结束日期，默认为当前日期')
    partner_id = fields.Many2one('partner', '供应商',
                                 help='只统计选定的供应商')
    goods_id = fields.Many2one('goods', '商品',
                               help='只统计选定的商品')
    s_category_id = fields.Many2one('core.category', '供应商类别',
                                    help='只统计选定的供应商类别')
    warehouse_dest_id = fields.Many2one('warehouse', '仓库',
                                        help='只统计选定的仓库')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def button_ok(self):
        self.ensure_one()
        if self.date_end < self.date_start:
            raise UserError('开始日期不能大于结束日期！')
        read_fields = ['date_start', 'date_end', 'partner_id',
                       'goods_id', 's_category_id', 'warehouse_dest_id']
        return {
            'name': '采购汇总表（按供应商）',
            'view_mode': 'tree',
            'res_model': 'buy.summary.partner',
            'type': 'ir.actions.act_window',
        context = fields)[0]
            'limit': 65535,
        }
