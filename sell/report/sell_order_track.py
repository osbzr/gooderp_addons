
import odoo.addons.decimal_precision as dp
from odoo import fields, models, api


class SellOrderTrack(models.TransientModel):
    _name = 'sell.order.track'
    _description = '销售订单跟踪表'

    goods_code = fields.Char('商品编码')
    goods_id = fields.Many2one('goods', '商品名称')
    attribute = fields.Char('属性')
    uom = fields.Char('单位')
    date = fields.Date('订单日期')
    order_name = fields.Char('销售订单编号')
    user_id = fields.Many2one('res.users', '销售员')
    partner_id = fields.Many2one('partner', '客户')
    warehouse_id = fields.Many2one('warehouse', '仓库')
    goods_state = fields.Char('状态')
    qty = fields.Float('数量', digits=dp.get_precision('Quantity'))
    amount = fields.Float('销售额', digits=dp.get_precision('Amount'))  # 商品的价税合计
    qty_not_out = fields.Float('未出库数量', digits=dp.get_precision('Quantity'))
    delivery_date = fields.Date('要求交货日期')
    wh_out_date = fields.Date('出库日期')
    note = fields.Char('备注')
    type = fields.Selection([('sell', '销货'), ('return', '退货')], string='单据类型')

    @api.multi
    def view_detail(self):
        '''查看明细按钮'''
        self.ensure_one()
        order = self.env['sell.order'].search([('name', '=', self.order_name)])
        if order:
            view = self.env.ref('sell.sell_order_form')
            return {
                'name': '销货订单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'sell.order',
                'type': 'ir.actions.act_window',
                'res_id': order.id,
            }
