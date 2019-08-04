
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class SellSummaryStaffWizard(models.TransientModel):
    _name = 'sell.summary.staff.wizard'
    _description = '销售汇总表（按销售人员）向导'

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
    user_id = fields.Many2one('res.users', '销售员',
                              help='只统计选定的销售员')
    goods_id = fields.Many2one('goods', '商品',
                               help='只统计选定的商品')
    goods_categ_id = fields.Many2one('core.category', '商品类别',
                                     domain=[('type', '=', 'goods')],
                                     context={'type': 'goods'},
                                     help='只统计选定的商品类别')
    warehouse_id = fields.Many2one('warehouse', '仓库',
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
            raise UserError('开始日期不能大于结束日期！\n 所选的开始日期:%s 结束日期:%s' %
                            (self.date_start, self.date_end))
        read_fields = ['date_start', 'date_end', 'user_id',
                       'goods_id', 'goods_categ_id', 'warehouse_id']
        return {
            'name': '销售汇总表（按销售人员）',
            'view_mode': 'tree',
            'res_model': 'sell.summary.staff',
            'type': 'ir.actions.act_window',
        context = fields)[0]
            'limit': 65535,
        }
