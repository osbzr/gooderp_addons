# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class SellToBuyWizard(models.TransientModel):
    _name = 'sell.to.buy.wizard'
    _description = u'根据销货订单生成购货订单向导'

    sell_line_ids = fields.Many2many(
        'sell.order.line',
        string=u'销货单行',
        help=u'对应的销货订单行')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    def _get_vals(self, order, line):
        '''返回创建 buy order line 时所需数据'''
        return {
            'order_id': order.id,
            'goods_id': line.goods_id.id,
            'attribute_id': line.attribute_id.id,
            'quantity': line.quantity,
            'uom_id': line.uom_id.id,
            'discount_rate': line.discount_rate,
            'discount_amount': line.discount_amount,
            'tax_rate': line.tax_rate,
            'note': line.note or '',
            'sell_line_id': line.id,    # sell_line_id写入到购货订单行上
        }

    @api.multi
    def button_ok(self):
        '''生成按钮，复制销货订单行到购货订单中'''
        for wizard in self:
            if not wizard.sell_line_ids:
                raise UserError(u'销货订单行不能为空')
            active_id = self.env.context.get('active_id')
            buy_lines = []
            order_dict = {} # 用来判断勾选行是否来自同一张销货订单

            if active_id:
                order = self.env['buy.order'].browse(active_id)
            for line in wizard.sell_line_ids:
                if not order_dict.has_key(line.order_id):
                    order_dict[line.order_id] = line
                else:
                    order_dict[line.order_id] += line
            if len(order_dict.keys()) > 1:
                raise UserError(u'一次只能勾选同一张销货订单的行')
            for line in wizard.sell_line_ids:
                buy_lines.append(self._get_vals(order, line))
                line.is_bought = True
            # 将销货订单行复制到购货订单
            order.write({
                'sell_id': order_dict.keys()[0].id,
                'line_ids': [(0, 0, line) for line in buy_lines]})
            # 价格取自商品的成本字段或者供应商供货价格
            for line in order.line_ids:
                line.onchange_goods_id()
                line.onchange_discount_rate()

            return True
