
import odoo.addons.decimal_precision as dp
from odoo import fields, models, api, tools


class BuyOrderDetail(models.Model):
    _name = 'buy.order.detail'
    _description = '采购明细表'
    _auto = False

    date = fields.Date('采购日期')
    order_name = fields.Char('采购单据号')
    type = fields.Char('业务类型')
    partner_id = fields.Many2one('partner', '供应商')
    goods_code = fields.Char('商品编码')
    goods_id = fields.Many2one('goods', '商品名称')
    attribute = fields.Char('属性')
    warehouse_dest_id = fields.Many2one('warehouse', '仓库')
    qty = fields.Float('数量', digits=dp.get_precision('Quantity'))
    uom = fields.Char('单位')
    price = fields.Float('单价', digits=dp.get_precision('Price'))
    amount = fields.Float(
        '采购金额', digits=dp.get_precision('Amount'))  # 商品的购货金额
    tax_amount = fields.Float('税额', digits=dp.get_precision('Amount'))
    subtotal = fields.Float('价税合计', digits=dp.get_precision('Amount'))
    note = fields.Char('备注')

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'buy_order_detail')
        cr.execute("""
            CREATE or REPLACE VIEW buy_order_detail AS (
                SELECT  MIN(wml.id) AS id,
                    wm.date AS date,
                    wm.name AS order_name,
                    (CASE WHEN wm.origin = 'buy.receipt.buy' THEN '购货'
                        ELSE '退货' END) AS type,
                    wm.partner_id AS partner_id,
                    goods.code AS goods_code,
                    goods.id AS goods_id,
                    attr.name AS attribute,
                    wh.id AS warehouse_dest_id,
                    SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.goods_qty
                        ELSE - wml.goods_qty END) AS qty,
                    uom.name AS uom,
                    wml.price AS price,
                    SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.amount
                        ELSE - wml.amount END) AS amount,
                    SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.tax_amount
                        ELSE - wml.tax_amount END) AS tax_amount,
                    SUM(CASE WHEN wm.origin = 'buy.receipt.buy' THEN wml.subtotal
                        ELSE - wml.subtotal END) AS subtotal,
                    wml.note AS note

                FROM wh_move_line AS wml
                    LEFT JOIN wh_move wm ON wml.move_id = wm.id
                    LEFT JOIN partner ON wm.partner_id = partner.id
                    LEFT JOIN goods ON wml.goods_id = goods.id
                    LEFT JOIN attribute AS attr ON wml.attribute_id = attr.id
                    LEFT JOIN warehouse AS wh ON wml.warehouse_id = wh.id
                         OR wml.warehouse_dest_id = wh.id
                    LEFT JOIN uom ON goods.uom_id = uom.id
                    LEFT JOIN buy_receipt AS br ON wm.id = br.buy_move_id

                WHERE wml.state = 'done'
                  AND wm.origin like 'buy.receipt%%'
                  AND wh.type = 'stock'

                GROUP BY wm.date, wm.name, origin, partner_id,
                    goods_code, goods.id, attribute, wh.id, uom,
                    wml.price, wml.note
                )
        """)

    @api.multi
    def view_detail(self):
        '''查看明细按钮'''
        self.ensure_one()
        order = self.env['buy.receipt'].search(
            [('name', '=', self.order_name)])
        if order:
            if not order.is_return:
                view = self.env.ref('buy.buy_receipt_form')
            else:
                view = self.env.ref('buy.buy_return_form')

            return {
                'name': '采购入库单',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view.id, 'form')],
                'res_model': 'buy.receipt',
                'type': 'ir.actions.act_window',
                'res_id': order.id,
            }
