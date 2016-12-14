# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
class wh_move(models.Model):
    _name = 'wh.move'

    MOVE_STATE = [
        ('draft', u'草稿'),
        ('done', u'已审核'),
    ]
    
    @api.one
    @api.depends('line_out_ids','line_in_ids')
    def _compute_total_qty(self):
        goods_total = 0
        if self.line_in_ids:
            # 入库产品总数
            goods_total = sum(line.goods_qty for line in self.line_in_ids)
        elif self.line_out_ids:
            # 出库产品总数
            goods_total = sum(line.goods_qty for line in self.line_out_ids)
        self.total_qty = goods_total

    @api.model
    def _get_default_warehouse_impl(self):
        if self.env.context.get('warehouse_type', 'stock'):
            return self.env['warehouse'].get_warehouse_by_type(
                    self.env.context.get('warehouse_type', 'stock'))

    @api.model
    def _get_default_warehouse_dest_impl(self):
        if self.env.context.get('warehouse_dest_type', 'stock'):
            return self.env['warehouse'].get_warehouse_by_type(
                    self.env.context.get('warehouse_dest_type', 'stock'))

    @api.model
    def _get_default_warehouse(self):
        '''获取调出仓库'''
        return self._get_default_warehouse_impl()

    @api.model
    def _get_default_warehouse_dest(self):
        '''获取调入仓库'''
        return self._get_default_warehouse_dest_impl()

    origin = fields.Char(u'移库类型', required=True,
                         help=u'移库类型')
    name = fields.Char(u'单据编号', copy=False, default='/',
                       help=u'单据编号，创建时会自动生成')
    state = fields.Selection(MOVE_STATE, u'状态', copy=False, default='draft',
                             help=u'移库单状态标识，新建时状态为未审核;审核后状态为已审核')
    partner_id = fields.Many2one('partner', u'业务伙伴', ondelete='restrict',
                                 help=u'该单据对应的业务伙伴')
    date = fields.Date(u'单据日期', required=True, copy=False, default=fields.Date.context_today,
                       help=u'单据创建日期，默认为当前天')
    warehouse_id = fields.Many2one('warehouse', u'调出仓库',
                                   ondelete='restrict',
                                   required=True,
                                   default=_get_default_warehouse,
                                   help=u'移库单的来源仓库')
    warehouse_dest_id = fields.Many2one('warehouse', u'调入仓库',
                                        ondelete='restrict',
                                        required=True,
                                        default=_get_default_warehouse_dest,
                                        help=u'移库单的目的仓库')
    approve_uid = fields.Many2one('res.users', u'审核人',
                                  copy=False, ondelete='restrict',
                                  help=u'移库单的审核人')
    approve_date = fields.Datetime(u'审核日期', copy=False)
    line_out_ids = fields.One2many('wh.move.line', 'move_id', u'出库明细',
                                   domain=[('type', '=', 'out')],
                                   context={'type': 'out'}, copy=True,
                                   help=u'出库类型的移库单对应的出库明细')
    line_in_ids = fields.One2many('wh.move.line', 'move_id', u'入库明细',
                                  domain=[('type', '=', 'in')],
                                  context={'type': 'in'}, copy=True,
                                  help=u'入库类型的移库单对应的入库明细')
    note = fields.Text(u'备注',
                       help=u'可以为该单据添加一些需要的标识信息')
    total_qty = fields.Integer(u'产品总数', compute=_compute_total_qty, store=True,
                               help=u'该移库单的入/出库明细行包含的产品总数')
    staff_id = fields.Many2one('staff', u'经办人',
                               default=lambda self: self.env.user.employee_ids and self.env.user.employee_ids[0])

    def scan_barcode_move_line_operation(self, line, conversion):
        line.goods_qty += 1
        line.goods_uos_qty = line.goods_qty / conversion
        return True

    def scan_barcode_inventory_line_operation(self, line, conversion):
        '''盘点单明细行数量增加'''
        line.inventory_qty += 1
        line.inventory_uos_qty = line.inventory_qty / conversion
        line.difference_qty += 1
        line.difference_uos_qty = line.difference_qty / conversion

        return True

    def scan_barcode_move_in_out_operation(self, move, att, conversion, goods, val):
        create_line =False
        for line in move.line_out_ids:
            line.cost_unit = line.goods_id.price if val['type'] == 'out' else line.goods_id.cost
            # 如果产品属性上存在条码，且明细行上已经存在该产品，则数量累加
            if att and line.attribute_id.id == att.id:
                create_line = self.scan_barcode_move_line_operation(line, conversion)
            # 如果产品上存在条码，且明细行上已经存在该产品，则数量累加
            elif goods and line.goods_id.id == goods.id:
                create_line = self.scan_barcode_move_line_operation(line, conversion)
        return create_line

    def scan_barcode_sell_or_buy_operation(self, move, att, conversion, goods, val):
        create_line = False
        for line in move.line_in_ids:
            line.price_taxed = line.goods_id.price if val['type'] == 'out' else line.goods_id.cost
            # 如果产品属性上存在条码
            if att and line.attribute_id.id == att.id:
                create_line = self.scan_barcode_move_line_operation(line, conversion)
            # 如果产品上存在条码
            elif goods and line.goods_id.id == goods.id:
                create_line = self.scan_barcode_move_line_operation(line, conversion)
        return create_line

    def scan_barcode_inventory_operation(self, move, att, conversion, goods, val):
        '''盘点单扫码操作'''
        create_line = False
        for line in move.line_ids:
            # 如果产品属性上存在条码 或 产品上存在条码
            if (att and line.attribute_id == att) or (goods and line.goods_id == goods):
                create_line = self.scan_barcode_inventory_line_operation(line, conversion)
        return create_line

    def scan_barcode_each_model_operation(self, model_name, order_id, att, goods,conversion):
        val ={}
        create_line =False
        if model_name in ['wh.out', 'wh.in']:
            move = self.env[model_name].browse(order_id).move_id
            # 在其他出库单上扫描条码
        if model_name == 'wh.out':
            val['type'] = 'out'
            create_line = self.scan_barcode_move_in_out_operation(move, att, conversion, goods,val)
            # 在其他入库单上扫描条码
        if model_name == 'wh.in':
            val['type'] = 'in'
            create_line = self.scan_barcode_move_in_out_operation(move, att, conversion, goods,val)
            # 销售出入库单的二维码
        if model_name == 'sell.delivery':
            move = self.env[model_name].browse(order_id).sell_move_id
            if self.env[model_name].browse(order_id).is_return:
                val['type'] = 'in'
                create_line = self.scan_barcode_sell_or_buy_operation(move, att, conversion, goods,val)
            else:
                val['type'] = 'out'
                create_line = self.scan_barcode_sell_or_buy_operation(move, att, conversion, goods,val)
                # 采购出入库单的二维码
        if model_name == 'buy.receipt':
            move = self.env[model_name].browse(order_id).buy_move_id
            if self.env[model_name].browse(order_id).is_return:
                val['type'] = 'out'
                create_line = self.scan_barcode_sell_or_buy_operation(move, att, conversion, goods,val)
            else:
                val['type'] = 'in'
                create_line = self.scan_barcode_sell_or_buy_operation(move, att, conversion, goods,val)

            # 调拔单的扫描条码
        if model_name == 'wh.internal':
            move = self.env[model_name].browse(order_id).move_id
            val['type'] = 'internal'
            create_line = self.scan_barcode_move_in_out_operation(move, att, conversion, goods,val)

        # 盘点单的扫码
        if model_name == 'wh.inventory':
            move = self.env[model_name].browse(order_id)
            val['type'] = 'in'
            create_line = self.scan_barcode_inventory_operation(move, att, conversion, goods, val)

        return move, create_line, val

    def prepare_move_line_data(self, att, val, goods, move):
        if att:
            goods_id = att.goods_id.id
            uos_id = att.goods_id.uos_id.id
            uom_id = att.goods_id.uom_id.id
            attribute_id = att.id
            conversion = att.goods_id.conversion
            if val['type'] in ('in','internal'):
                # 入库操作取产品的成本
                price = cost_unit = att.goods_id.cost
            elif val['type'] == 'out':
                # 出库操作取产品的零售价
                price = cost_unit = att.goods_id.price

            # 伪装成出库明细，代码结构问题
            if val['type'] == 'internal':
                val['type'] = 'out'

        elif goods:
            goods_id = goods.id
            uos_id = goods.uos_id.id
            uom_id = goods.uom_id.id
            attribute_id = False
            conversion = goods.conversion
            if val['type'] in ('in','internal'):
                # 入库操作取产品的成本
                price = cost_unit = goods.cost
            elif val['type'] == 'out':
                # 出库操作取产品的零售价
                price = cost_unit = goods.price

            # 伪装成出库明细，代码结构问题
            if val['type'] == 'internal':
                val['type'] = 'out'

        if move._name != 'wh.inventory':
            val.update({
                'goods_id': goods_id,
                'attribute_id': attribute_id,
                'warehouse_id': move.warehouse_id.id,
                'warehouse_dest_id': move.warehouse_dest_id.id,
                'goods_uos_qty': 1.0 / conversion,
                'uos_id': uos_id,
                'goods_qty': 1,
                'uom_id': uom_id,
                'price_taxed': price,
                'cost_unit': cost_unit,
                'move_id': move.id})
        else:
            val.update({
                'goods_id': goods_id,
                'attribute_id': attribute_id,
                'warehouse_id': move.warehouse_id.id,
                'inventory_uos_qty': 1.0 / conversion,
                'uos_id': uos_id,
                'inventory_qty': 1,
                'uom_id': uom_id,
                'real_uos_qty': 0,
                'real_qty': 0,
                'difference_uos_qty': 1.0 / conversion,
                'difference_qty': 1,
                'inventory_id': move.id})
        return val

    @api.model
    def check_barcode(self, model_name, order_id, att, goods):
        pass

    @api.model
    def scan_barcode(self,model_name,barcode,order_id):
        att = self.env['attribute'].search([('ean','=',barcode)])
        goods = self.env['goods'].search([('barcode', '=', barcode)])
        line_model = (model_name == 'wh.inventory' and 'wh.inventory.line'
                      or 'wh.move.line')

        if not att and not goods:
            raise UserError(u'ean为  %s 的产品不存在' % (barcode))
        else:
            self.check_barcode(model_name, order_id, att, goods)
            conversion = att and att.goods_id.conversion or goods.conversion
            move, create_line, val = self.scan_barcode_each_model_operation(model_name, order_id, att, goods,conversion)
            if not create_line:
                self.env[line_model].create(self.prepare_move_line_data(att, val, goods, move))

    @api.multi
    def unlink(self):
        for move in self:
            if move.state == 'done':
                raise UserError(u'不可以删除已经完成的单据')

        return super(wh_move, self).unlink()

    def prev_approve_order(self):
        for order in self:
            if not order.line_out_ids and not order.line_in_ids:
                raise UserError(u'单据的明细行不可以为空')

    @api.multi
    def approve_order(self):
        for order in self:
            order.prev_approve_order()
            order.line_out_ids.action_done()
            order.line_in_ids.action_done()

        return self.write({
                'approve_uid': self.env.uid,
                'approve_date': fields.Datetime.now(self),
                'state': 'done',
            })

    def prev_cancel_approved_order(self):
        pass

    @api.multi
    def cancel_approved_order(self):
        for order in self:
            order.prev_cancel_approved_order()
            order.line_out_ids.action_cancel()
            order.line_in_ids.action_cancel()

        return self.write({
                'approve_uid': False,
                'approve_date': False,
                'state': 'draft',
            })


    @api.multi
    def check_goods_qty(self, goods, attribute, warehouse):
        '''SQL来取指定产品，属性，仓库，的当前剩余数量'''

        if attribute:
            change_conditions = "AND line.attribute_id = %s" % attribute.id
        elif goods:
            change_conditions = "AND line.goods_id = %s" % goods.id
        else:
            change_conditions = "AND 1 = 0"
        self.env.cr.execute('''
                       SELECT sum(line.qty_remaining) as qty
                       FROM wh_move_line line

                       WHERE line.warehouse_dest_id = %s
                             AND line.state = 'done'
                             %s
                   ''' % (warehouse.id, change_conditions,))
        return self.env.cr.fetchone()

    @api.multi
    def create_zero_wh_in(self,wh_in,model_name):
        for line in wh_in.line_out_ids:
            vals={}
            result = False
            if line.goods_id.no_stock:
                continue
            else:
                result = self.env['wh.move'].check_goods_qty(line.goods_id, line.attribute_id, wh_in.warehouse_id)
                result = result[0] or 0
            if line.goods_qty > result and not line.lot_id and not self.env.context.get('wh_in_line_ids'):
                #在销售出库时如果临时缺货，自动生成一张盘盈入库单
                today = fields.Datetime.now()
                vals.update({
                        'type':'inventory',
                        'warehouse_id':self.env.ref('warehouse.warehouse_inventory').id,
                        'warehouse_dest_id':wh_in.warehouse_id.id,
                        'state':'done',
                        'date':today,
                        'line_in_ids':[(0, 0, {
                                    'goods_id':line.goods_id.id,
                                    'attribute_id':line.attribute_id.id,
                                    'goods_uos_qty':0,
                                    'uos_id':line.uos_id.id,
                                    'goods_qty':0,
                                    'uom_id':line.uom_id.id,
                                    'cost_unit':line.goods_id.cost,
                                    'state': 'done',
                                    'date': today,
                                                }
                                        )]
                            })
                return self.env[model_name].open_dialog('goods_inventory', {
                    'message': u'产品 %s 当前库存量不足，继续出售请点击确定，并及时盘点库存' % line.goods_id.name,
                    'args': [vals],
                })

            if line.goods_qty <= 0 or line.price_taxed < 0:
                raise UserError(u'产品 %s 的数量和含税单价不能小于0！' % line.goods_id.name)