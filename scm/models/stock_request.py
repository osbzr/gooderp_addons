# -*- coding: utf-8 -*-

from odoo import tools
import odoo.addons.decimal_precision as dp
from odoo import models, fields, api
from odoo.exceptions import UserError

# 补货申请单确认状态可选值
STOCK_REQUEST_STATES = [
    ('unsubmit', u'未提交'),
    ('draft', u'未确认'),
    ('done', u'已确认'),
    ('cancel', u'已作废')]


class StockRequest(models.Model):
    _name = 'stock.request'
    _inherit = ['mail.thread']
    _description = u'补货申请'

    name = fields.Char(u'编号')
    date = fields.Date(u'日期',
                       default=lambda self: fields.Date.context_today(self),
                       states={'done': [('readonly', True)]})
    user_id = fields.Many2one(
        'res.users',
        u'经办人',
        ondelete='restrict',
        states={'done': [('readonly', True)]},
        default=lambda self: self.env.user,
        help=u'单据经办人',
    )
    line_ids = fields.One2many('stock.request.line',
                               'request_id',
                               u'补货申请行',
                               states={'done': [('readonly', True)]})
    state = fields.Selection(STOCK_REQUEST_STATES, u'确认状态', readonly=True,
                             help=u"补货申请的确认状态", copy=False,
                             index=True,
                             default='unsubmit')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.one
    def stock_query(self):
        ''' 点击 查询库存 按钮 生成补货申请行
                                    每行一个商品一个属性的 数量，补货数量
         '''
        goods = self.env['goods'].search([('no_stock', '=', False)])

        for good in goods:
            qty = 0  # 当前数量
            to_delivery_qty = 0  # 未发货数量
            to_receipt_qty = 0  # 未到货数量
            to_sell_qty = 0  # 未确认销货数量
            to_buy_qty = 0  # 未确认购货数量

            wh_move_lines = self.env['wh.move.line'].search(
                [('goods_id', '=', good.id)])

            attribute_dict = {}
            to_delivery_dict = {}
            to_receipt_dict = {}
            to_sell_dict = {}
            to_buy_dict = {}
            for wh_move_line in wh_move_lines:
                # 计算当前数量
                if wh_move_line.state == 'done':
                    if wh_move_line.warehouse_dest_id.type == 'stock':  # 目的库位为库存库位
                        if wh_move_line.attribute_id:  # 商品存在属性
                            if wh_move_line.attribute_id not in attribute_dict:
                                attribute_dict.update(
                                    {wh_move_line.attribute_id: wh_move_line.qty_remaining})
                            else:
                                attribute_dict[wh_move_line.attribute_id] += wh_move_line.qty_remaining
                        else:  # 商品不存在属性
                            qty += wh_move_line.qty_remaining
                # 计算未发货和未到货数量
                else:
                    if wh_move_line.type == 'out':
                        if wh_move_line.attribute_id:  # 商品存在属性
                            if not to_delivery_dict.has_key(wh_move_line.attribute_id):
                                to_delivery_dict.update(
                                    {wh_move_line.attribute_id: wh_move_line.goods_qty})
                            else:
                                to_delivery_dict[wh_move_line.attribute_id] += wh_move_line.goods_qty
                        else:  # 商品不存在属性
                            to_delivery_qty += wh_move_line.goods_qty
                    else:
                        if wh_move_line.attribute_id:  # 商品存在属性
                            if not to_receipt_dict.has_key(wh_move_line.attribute_id):
                                to_receipt_dict.update(
                                    {wh_move_line.attribute_id: wh_move_line.goods_qty})
                            else:
                                to_receipt_dict[wh_move_line.attribute_id] += wh_move_line.goods_qty
                        else:  # 商品不存在属性
                            to_receipt_qty += wh_move_line.goods_qty
            # 计算未销货数量
            sell_order_lines = self.env['sell.order.line'].search([('goods_id', '=', good.id),
                                                                   ('order_id.state', '=', 'draft')])
            for line in sell_order_lines:
                if line.attribute_id:  # 商品存在属性
                    if not to_sell_dict.has_key(line.attribute_id):
                        to_sell_dict.update({line.attribute_id: line.quantity})
                    else:
                        to_sell_dict[line.attribute_id] += line.quantity
                else:  # 商品不存在属性
                    to_sell_qty += line.quantity
            # 计算未购货数量
            buy_order_lines = self.env['buy.order.line'].search([('goods_id', '=', good.id),
                                                                 ('order_id.state', '=', 'draft')])
            for line in buy_order_lines:
                if line.attribute_id:  # 商品存在属性
                    if not to_buy_dict.has_key(line.attribute_id):
                        to_buy_dict.update({line.attribute_id: line.quantity})
                    else:
                        to_buy_dict[line.attribute_id] += line.quantity
                else:  # 商品不存在属性
                    to_buy_qty += line.quantity

            # 如果组装单模板存在，is_buy置为False
            bom_line = self.env['wh.bom.line'].search([('goods_id', '=', good.id),
                                                       ('bom_id.type',
                                                        '=', 'assembly'),
                                                       ('type', '=', 'parent')])
            if bom_line:
                is_buy = False
            else:
                is_buy = True

            # 生成补货申请行
            qty_available = 0  # 可用库存
            if good.attribute_ids:  # 商品存在属性
                for attribute in good.attribute_ids:
                    qty = attribute in attribute_dict and attribute_dict[attribute] or 0
                    to_sell_qty = attribute in to_sell_dict and to_sell_dict[attribute] or 0
                    to_delivery_qty = attribute in to_delivery_dict and to_delivery_dict[
                        attribute] or 0
                    to_buy_qty = attribute in to_buy_dict and to_buy_dict[attribute] or 0
                    to_receipt_qty = attribute in to_receipt_dict and to_receipt_dict[
                        attribute] or 0
                    qty_available = qty + to_receipt_qty + \
                        to_buy_qty - to_delivery_qty - to_sell_qty
                    if qty_available < good.min_stock_qty:
                        self.env['stock.request.line'].create({
                            'request_id': self.id,
                            'goods_id': good.id,
                            'attribute_id': attribute.id,
                            'qty': qty,
                            'to_sell_qty': to_sell_qty,
                            'to_delivery_qty': to_delivery_qty,
                            'to_buy_qty': to_buy_qty,
                            'to_receipt_qty': to_receipt_qty,
                            'min_stock_qty': good.min_stock_qty,
                            'request_qty': good.min_stock_qty - qty_available,
                            'uom_id': good.uom_id.id,
                            'supplier_id': good.supplier_id and good.supplier_id.id or False,
                            'is_buy': is_buy,
                        })
            else:  # 商品不存在属性
                qty_available = qty + to_receipt_qty + \
                    to_buy_qty - to_delivery_qty - to_sell_qty
                if qty_available < good.min_stock_qty:
                    self.env['stock.request.line'].create({
                        'request_id': self.id,
                        'goods_id': good.id,
                        'qty': qty,
                        'to_sell_qty': to_sell_qty,
                        'to_delivery_qty': to_delivery_qty,
                        'to_buy_qty': to_buy_qty,
                        'to_receipt_qty': to_receipt_qty,
                        'min_stock_qty': good.min_stock_qty,
                        'request_qty': good.min_stock_qty - qty_available,
                        'uom_id': good.uom_id.id,
                        'supplier_id': good.supplier_id and good.supplier_id.id or False,
                        'is_buy': is_buy,
                    })

        self.state = 'draft'

    def _get_buy_order_line_data(self, line, buy_order):
        price_taxed = line.goods_id.cost
        for vendor_price in line.goods_id.vendor_ids:
            if vendor_price.vendor_id == buy_order.partner_id \
                    and line.request_qty >= vendor_price.min_qty:
                price_taxed = vendor_price.price
                break

        return {
            'order_id': buy_order.id,
            'goods_id': line.goods_id.id,
            'attribute_id': line.attribute_id and line.attribute_id.id or False,
            'uom_id': line.uom_id.id,
            'quantity': line.request_qty,
            'price_taxed': price_taxed,
            'note': u'补货申请单号：%s' % line.request_id.name
        }

    @api.one
    def stock_request_done(self):
        if self.state == 'done':
            raise UserError(u'请不要重复确认')
        todo_buy_lines = []  # 待生成购货订单
        todo_produce_lines = []  # 待生成组装单
        for line in self.line_ids:
            if line.is_buy:
                todo_buy_lines.append(line)
            else:
                todo_produce_lines.append(line)

        # 处理待生成组装单行
        while True:
            if not todo_produce_lines:
                break

            for line in todo_produce_lines:
                # 处理过的组装单行 移除
                todo_produce_lines.remove(line)

                if not line.request_qty:
                    continue

                # 如果组装单模板存在，创建组装单
                bom_line = self.env['wh.bom.line'].search([('goods_id', '=', line.goods_id.id),
                                                           ('bom_id.type',
                                                            '=', 'assembly'),
                                                           ('type', '=', 'parent')])
                if bom_line:
                    assembly = self.env['wh.assembly'].create({
                        'bom_id': bom_line.bom_id.id,
                        'goods_qty': 0,
                    })
                    assembly.onchange_bom()
                    assembly.goods_qty = line.request_qty
                    assembly.onchange_goods_qty()
                    assembly.note = assembly.note or ''
                    assembly.note += u' 补货申请单号：%s' % line.request_id.name

                    # 如果待处理行中有属性，则把它传至组装单的组合件行中
                    if line.attribute_id:
                        for line_in in assembly.line_in_ids:
                            line_in.attribute_id = line.attribute_id

                    for line_out in assembly.line_out_ids:
                        # 如果组装单模板存在，is_buy置为False
                        bom_line = self.env['wh.bom.line'].search([('goods_id', '=', line_out.goods_id.id),
                                                                   ('bom_id.type',
                                                                    '=', 'assembly'),
                                                                   ('type', '=', 'parent')])
                        if bom_line:
                            is_buy = False
                        else:
                            is_buy = True

                        request_line_ids = self.env['stock.request.line'].create({
                            'request_id': self.id,
                            'goods_id': line_out.goods_id.id,
                            'attribute_id': line_out.attribute_id and line_out.attribute_id.id or False,
                            'to_delivery_qty': line_out.goods_qty,
                            'request_qty': line_out.goods_qty,
                            'uom_id': line_out.goods_id.uom_id.id,
                            'supplier_id': line_out.goods_id.supplier_id and line_out.goods_id.supplier_id.id or False,
                            'is_buy': is_buy,
                        })
                        if is_buy:
                            todo_buy_lines.append(request_line_ids)
                        else:
                            todo_produce_lines.append(request_line_ids)

        # 处理待生成购货订单行
        for line in todo_buy_lines:
            if not line.request_qty:
                continue

            if not line.supplier_id:
                raise UserError(u'请输入补货申请行商品%s%s 的供应商。' % (
                    line.goods_id.name, line.attribute_id.name or ''))

            # 找供应商相同的购货订单
            buy_order = self.env['buy.order'].search([('partner_id', '=', line.supplier_id.id),
                                                      ('state', '=', 'draft')])
            if len(buy_order) >= 1:
                buy_order = buy_order[0]
            else:
                # 创建新的购货订单
                buy_order = self.env['buy.order'].with_context(warehouse_dest_type='stock').create({
                    'partner_id': line.supplier_id.id
                })
            # 找相同的采购单行
            buy_order_line = self.env['buy.order.line'].search([('order_id.partner_id', '=', line.supplier_id.id),
                                                                ('order_id.state',
                                                                 '=', 'draft'),
                                                                ('goods_id', '=',
                                                                 line.goods_id.id),
                                                                ('attribute_id', '=', line.attribute_id.id)])
            if len(buy_order_line) > 1:
                raise UserError(u'供应商%s 商品%s%s 存在多条未确认购货订单行。请联系采购人员处理。'
                                % (line.supplier_id.name, line.goods_id.name, line.attribute_id.name or ''))

            if buy_order_line:
                # 增加原订单行的商品数量
                buy_order_line.quantity += line.request_qty
                buy_order_line.note = buy_order_line.note or ''
                buy_order_line.note += u' %s' % (line.request_id.name)
            else:
                # 创建购货订单行
                vals = self._get_buy_order_line_data(line, buy_order)
                self.env['buy.order.line'].create(vals)

        self.state = 'done'


class StockRequestLine(models.Model):
    _name = 'stock.request.line'
    _description = u'补货申请行'

    request_id = fields.Many2one('stock.request', u'补货申请')
    goods_id = fields.Many2one('goods', u'商品')
    attribute_id = fields.Many2one('attribute', u'属性')
    qty = fields.Float(u'当前数量', digits=dp.get_precision('Quantity'))
    to_sell_qty = fields.Float(u'未确认销货数量', digits=dp.get_precision('Quantity'))
    to_delivery_qty = fields.Float(
        u'未发货数量', digits=dp.get_precision('Quantity'))
    to_buy_qty = fields.Float(u'未确认购货数量', digits=dp.get_precision('Quantity'))
    to_receipt_qty = fields.Float(
        u'未到货数量', digits=dp.get_precision('Quantity'))
    min_stock_qty = fields.Float(
        u'安全库存数量', digits=dp.get_precision('Quantity'))
    request_qty = fields.Float(u'申请补货数量', digits=dp.get_precision('Quantity'))
    to_produce_qty = fields.Float(
        u'未完工数量', digits=dp.get_precision('Quantity'))
    to_consume_qty = fields.Float(
        u'未投料数量', digits=dp.get_precision('Quantity'))
    uom_id = fields.Many2one('uom', u'单位')
    supplier_id = fields.Many2one('partner', u'供应商')
    is_buy = fields.Boolean(u'采购', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
