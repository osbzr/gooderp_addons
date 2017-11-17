# -*- coding: utf-8 -*-

from odoo.osv import osv
# from odoo.osv import fields
from utils import create_name, safe_division
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo.tools import float_compare, float_is_zero


class WhInventory(models.Model):
    _name = 'wh.inventory'
    _description = u'盘点单'
    _inherit = ['mail.thread']
    _order = 'date DESC, id DESC'

    INVENTORY_STATE = [
        ('draft', u'草稿'),
        ('query', u'查询中'),
        ('confirmed', u'待确认盘盈盘亏'),
        ('done', u'完成'),
    ]

    @api.model
    def _get_default_warehouse_impl(self):
        if self.env.context.get('warehouse_type', 'stock'):
            return self.env['warehouse'].get_warehouse_by_type(
                self.env.context.get('warehouse_type', 'stock'))

    @api.model
    def _get_default_warehouse(self):
        '''获取盘点仓库'''
        return self._get_default_warehouse_impl()

    date = fields.Date(u'日期', default=fields.Date.context_today,
                       help=u'盘点单创建日期，默认为当前天')
    name = fields.Char(u'名称', copy=False, default='/',
                       help=u'单据编号，创建时会自动生成')
    warehouse_id = fields.Many2one('warehouse', u'仓库', required=True, default=_get_default_warehouse,
                                   help=u'盘点单盘点的仓库')
    goods = fields.Many2many('goods', string=u'商品',
                             help=u'盘点单盘点的商品')
    out_id = fields.Many2one('wh.out', u'盘亏单据', copy=False,
                             help=u'盘亏生成的其他出库单单据')
    in_id = fields.Many2one('wh.in', u'盘盈单据', copy=False,
                            help=u'盘盈生成的其他入库单单据')
    state = fields.Selection(
        INVENTORY_STATE, u'状态', copy=False, default='draft',
        index=True,
        help=u'盘点单状态，新建时状态为草稿;'
             u'点击查询后为审核后状态为查询中;'
             u'有盘亏盘盈时生成的其他出入库单没有审核时状态为待确认盘盈盘亏;'
             u'盘亏盘盈生成的其他出入库单审核后状态为完成')
    line_ids = fields.One2many(
        'wh.inventory.line', 'inventory_id', u'明细', copy=False,
        help=u'盘点单的明细行')
    note = fields.Text(u'备注',
                       help=u'可以为该单据添加一些需要的标识信息')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def requery_inventory(self):
        self.delete_confirmed_wh()
        self.state = 'query'

    @api.model
    @create_name
    def create(self, vals):
        return super(WhInventory, self).create(vals)

    @api.multi
    def unlink(self):
        for inventory in self:
            inventory.delete_confirmed_wh()

        return super(WhInventory, self).unlink()

    def delete_confirmed_wh(self):
        for inventory in self:
            if inventory.state == 'confirmed':
                if (inventory.out_id and inventory.out_id.state == 'done') \
                        or (inventory.in_id and inventory.in_id.state == 'done'):
                    raise UserError(u'请先反审核掉相关的盘盈盘亏单据')
                else:
                    inventory.out_id.unlink()
                    inventory.in_id.unlink()

        return True

    def check_done(self):
        for inventory in self:
            if inventory.state == 'confirmed' and \
                (not inventory.out_id or inventory.out_id.state == 'done') and \
                    (not inventory.in_id or inventory.in_id.state == 'done'):
                self.state = 'done'
                return True
            if inventory.state == 'done' and \
                (not inventory.out_id or inventory.out_id.state != 'done') and \
                    (not inventory.in_id or inventory.in_id.state != 'done'):
                self.state = 'confirmed'
                return True
        return False

    @api.multi
    def open_out(self):
        for inventory in self:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'wh.out',
                'view_mode': 'form',
                'res_id': inventory.out_id.id,
            }

    @api.multi
    def open_in(self):
        for inventory in self:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'wh.in',
                'view_mode': 'form',
                'res_id': inventory.in_id.id,
            }

    def delete_line(self):
        self.line_ids.unlink()

    def create_losses_out(self, inventory, out_line):
        inventory_warehouse = self.env.ref('warehouse.warehouse_inventory')
        out_vals = {
            'warehouse_dest_id': inventory_warehouse.id,
            'warehouse_id': inventory.warehouse_id.id,
            'type': 'inventory',
            'line_out_ids': [],
        }

        for line in out_line:
            out_vals['line_out_ids'].append(
                [0, False, line.get_move_line(wh_type='out')])

        out_id = self.env['wh.out'].create(out_vals)
        inventory.out_id = out_id

    def create_overage_in(self, inventory, in_line):
        inventory_warehouse = self.env.ref('warehouse.warehouse_inventory')
        in_vals = {
            'warehouse_dest_id': inventory.warehouse_id.id,
            'warehouse_id': inventory_warehouse.id,
            'type': 'inventory',
            'line_in_ids': [],
        }

        for line in in_line:
            in_vals['line_in_ids'].append(
                [0, False, line.get_move_line(wh_type='in')])

        in_id = self.env['wh.in'].create(in_vals)
        inventory.in_id = in_id

    @api.multi
    def generate_inventory(self):
        for inventory in self:
            out_line, in_line = [], []
            for line in inventory.line_ids:
                if line.difference_qty < 0:
                    out_line.append(line)
                elif line.difference_qty > 0:
                    in_line.append(line)

            if out_line:
                self.create_losses_out(inventory, out_line)

            if in_line:
                self.create_overage_in(inventory, in_line)

            if len(out_line) + len(in_line) == 0:
                inventory.state = 'done'

            if out_line or in_line:
                inventory.state = 'confirmed'

        return True

    def get_line_detail(self):
        for inventory in self:
            sql_text = '''
                SELECT wh.id as warehouse_id,
                       goods.id as goods_id,
                       line.attribute_id as attribute_id,
                       line.lot as lot,
                       uom.id as uom_id,
                       uos.id as uos_id,
                       sum(line.qty_remaining) as qty,
                       sum(line.uos_qty_remaining) as uos_qty

                FROM wh_move_line line
                LEFT JOIN goods goods ON line.goods_id = goods.id
                    LEFT JOIN uom uom ON goods.uom_id = uom.id
                    LEFT JOIN uom uos ON goods.uos_id = uos.id
                LEFT JOIN warehouse wh ON line.warehouse_dest_id = wh.id

                WHERE line.qty_remaining != 0
                  AND wh.type = 'stock'
                  AND line.state = 'done'
                  %s

                GROUP BY
                  wh.id, line.lot, line.attribute_id, goods.id, uom.id, uos.id

                ORDER BY
                    goods.id, line.lot
            '''

            extra_text = ' AND wh.id = %s' % inventory.warehouse_id.id

            if inventory.goods:
                goods_ids = inventory.goods.ids
                goods_ids.append(0)
                extra_text += " AND goods.id IN {ids}".format(
                    ids=tuple(set(goods_ids)))

            inventory.env.cr.execute(sql_text % extra_text)
            res = inventory.env.cr.dictfetchall()
            for line in res:
                # 盘点单查询的盘点数量不应该包含移库在途的 #1358
                for int_line in self.env['wh.move.line'].search(
                        [('goods_id', '=', line['goods_id']),
                         ('attribute_id', '=', line['attribute_id']),
                         ('lot_id', '=', line['lot']),
                         ('warehouse_id', '=', line['warehouse_id']),
                         ('type', '=', 'internal')]):
                    line['qty'] -= int_line.goods_qty
                    line['uos_qty'] -= int_line.goods_uos_qty
                if not line['qty']:
                    res.remove(line)
            return res

    @api.multi
    def query_inventory(self):
        line_obj = self.env['wh.inventory.line']
        for inventory in self:
            inventory.delete_line()
            line_ids = inventory.get_line_detail()
            for line in line_ids:
                line_obj.create_wh_inventory_line_by_data(inventory.id, line)
            if line_ids:
                inventory.state = 'query'
        return True


class WhInventoryLine(models.Model):
    _name = 'wh.inventory.line'
    _description = u'盘点单明细'

    LOT_TYPE = [
        ('out', u'出库'),
        ('in', u'入库'),
        ('nothing', u'不做处理'),
    ]

    @api.multi
    @api.depends('inventory_qty', 'real_qty', 'inventory_uos_qty', 'real_uos_qty')
    def _get_difference_qty(self):
        for line in self:
            line.difference_qty = line.inventory_qty - line.real_qty
            line.difference_uos_qty = line.inventory_uos_qty - line.real_uos_qty

            if float_is_zero(line.difference_qty, 2) and not float_is_zero(line.difference_uos_qty, 2):
                line.difference_qty = line.difference_uos_qty * line.goods_id.conversion
            if not float_is_zero(line.difference_qty, 2) and line.difference_uos_qty == 0:
                line.difference_uos_qty = line.difference_qty / line.goods_id.conversion

    @api.multi
    @api.depends('inventory_uos_qty', 'real_uos_qty')
    def _get_difference_uos_qty(self):
        for line in self:
            line.difference_uos_qty = line.inventory_uos_qty - line.real_uos_qty

    inventory_id = fields.Many2one('wh.inventory', u'盘点', ondelete='cascade',
                                   help=u'盘点单行对应的盘点单')
    warehouse_id = fields.Many2one('warehouse', u'仓库', required=True, ondelete='restrict',
                                   help=u'盘点单行对应的仓库')
    goods_id = fields.Many2one('goods', u'商品', required=True, ondelete='restrict',
                               help=u'盘点单行对应的商品')
    attribute_id = fields.Many2one('attribute', u'属性', ondelete='restrict',
                                   help=u'盘点单行对应的商品的属性')
    using_batch = fields.Boolean(
        related='goods_id.using_batch', string=u'批号管理',
        help=u'盘点单行对应的商品是否使用批号管理，是True否则False')
    force_batch_one = fields.Boolean(
        related='goods_id.force_batch_one', string=u'每批号数量为1',
        help=u'盘点单行对应的商品是否使用每批号数量为1，是True否则False')
    lot = fields.Char(u'批号',
                      help=u'盘点单行对应的商品批号')
    new_lot = fields.Char(u'盘盈批号',
                          help=u'盘点单行对应的商品盘盈批号')
    new_lot_id = fields.Many2one('wh.move.line', u'盘亏批号',
                                 ondelete='restrict',
                                 help=u'盘点单行对应的商品盘亏批号')
    lot_type = fields.Selection(LOT_TYPE, u'批号类型', default='nothing',
                                help=u'批号类型: 出库、入库、不做处理')
    uom_id = fields.Many2one('uom', u'单位', ondelete='restrict',
                             help=u'盘点单行对应的商品的计量单位')
    uos_id = fields.Many2one('uom', u'辅助单位', ondelete='restrict',
                             help=u'盘点单行对应的商品的辅助单位')
    real_qty = fields.Float(
        u'账面数量', digits=dp.get_precision('Quantity'),
        help=u'盘点单行对应的商品的账面数量')
    real_uos_qty = fields.Float(
        u'账面辅助数量', digits=dp.get_precision('Quantity'),
        help=u'盘点单行对应的商品的账面辅助数量')
    inventory_qty = fields.Float(
        u'实际数量', digits=dp.get_precision('Quantity'),
        required=True,
        help=u'盘点单行对应的商品的实际数量')
    inventory_uos_qty = fields.Float(
        u'实际辅助数量', digits=dp.get_precision('Quantity'),
        required=True,
        help=u'盘点单行对应的商品的实际辅助数量')
    difference_qty = fields.Float(
        u'差异数量', digits=dp.get_precision('Quantity'),
        compute='_get_difference_qty',
        help=u'盘点单行对应的商品的差异数量')
    difference_uos_qty = fields.Float(
        u'差异辅助数量', digits=dp.get_precision('Quantity'),
        compute='_get_difference_uos_qty',
        help=u'盘点单行对应的商品的差异辅助数量')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    def check_difference_identical(self):
        if self.difference_qty * self.difference_uos_qty < 0:
            self.inventory_qty = self.real_qty
            self.inventory_uos_qty = self.real_uos_qty

            return {'warning': {
                'title': u'错误',
                'message': u'盘盈盘亏数量应该与辅助单位的盘盈盘亏数量盈亏方向一致',
            }}

    def create_wh_inventory_line_by_data(self, inventory_id, line_data):
        self.create({
            'inventory_id': inventory_id,
            'warehouse_id': line_data.get('warehouse_id'),
            'goods_id': line_data.get('goods_id'),
            'attribute_id': line_data.get('attribute_id'),
            'lot': line_data.get('lot'),
            'uom_id': line_data.get('uom_id'),
            'uos_id': line_data.get('uos_id'),
            'real_qty': line_data.get('qty'),
            'real_uos_qty': line_data.get('uos_qty'),
            'inventory_qty': line_data.get('qty'),
            'inventory_uos_qty': line_data.get('uos_qty'),
        })

    def line_role_back(self):
        self.inventory_qty = self.real_qty
        self.inventory_uos_qty = self.real_uos_qty
        self.difference_qty = 0
        self.difference_uos_qty = 0
        self.new_lot = ''
        self.new_lot_id = False
        self.lot_type = 'nothing'

    @api.multi
    @api.onchange('inventory_qty')
    def onchange_qty(self):
        self.ensure_one()

        if self.goods_id and self.goods_id.using_batch:
            if self.goods_id.force_batch_one and self.difference_qty:
                flag = self.difference_qty > 0 and 1 or -1
                if abs(self.difference_qty) != 1:
                    self.line_role_back()
                    return {'warning': {
                        'title': u'警告',
                        'message': u'商品上设置了序号为1，此时一次只能盘亏或盘盈一个商品数量',
                    }}

            if self.difference_qty > 0:
                self.lot_type = 'in'
                self.new_lot = self.new_lot or self.lot
                self.new_lot_id = False
            elif self.difference_qty < 0:
                self.lot_type = 'out'
                self.new_lot = ''
            else:
                self.lot_type = 'nothing'
                self.new_lot_id = False
                self.new_lot = ''

        return self.check_difference_identical()

    @api.onchange('inventory_uos_qty')
    def onchange_uos_qty(self):
        self.inventory_qty = self.goods_id.conversion_unit(
            self.inventory_uos_qty)

    def get_move_line(self, wh_type='in', context=None):
        inventory_warehouse = self.env['warehouse'] \
            .get_warehouse_by_type('inventory')
        for inventory in self:
            cost, cost_unit = inventory.goods_id. \
                get_suggested_cost_by_warehouse(
                    inventory.warehouse_id, abs(inventory.difference_qty),
                    lot_id=inventory.new_lot_id,
                    attribute=inventory.attribute_id)

            res = {
                'type': wh_type,
                'lot': inventory.new_lot,
                'lot_id': inventory.new_lot_id.id,
                'goods_id': inventory.goods_id.id,
                'attribute_id': inventory.attribute_id.id,
                'uom_id': inventory.uom_id.id,
                'uos_id': inventory.uos_id.id,
                'cost_unit': cost_unit,
                'cost': cost,
            }

            difference_qty, difference_uos_qty = abs(
                inventory.difference_qty), abs(inventory.difference_uos_qty)

            # 差异数量为0，且差异辅助数量不为0时，用差异辅助数量。否则用差差异数量
            if float_is_zero(difference_qty, 2) and not float_is_zero(difference_uos_qty, 2):
                res.update({'goods_uos_qty': difference_uos_qty})
            else:
                res.update({'goods_qty': difference_qty})

            return res


class WhOut(models.Model):
    _inherit = 'wh.out'

    inventory_ids = fields.One2many('wh.inventory', 'out_id', u'盘点单',
                                    help=u'其他出库单行对应的盘点单行，盘亏的情况')

    @api.multi
    def approve_order(self):
        res = super(WhOut, self).approve_order()
        for order in self:
            order.inventory_ids.check_done()

        return res

    @api.multi
    def cancel_approved_order(self):
        res = super(WhOut, self).cancel_approved_order()
        for order in self:
            order.inventory_ids.check_done()

        return res


class WhIn(models.Model):
    _inherit = 'wh.in'

    inventory_ids = fields.One2many('wh.inventory', 'in_id', u'盘点单',
                                    help=u'其他入库单行对应的盘点单行，盘盈的情况')

    @api.multi
    def approve_order(self):
        res = super(WhIn, self).approve_order()
        for order in self:
            order.inventory_ids.check_done()

        return res

    @api.multi
    def cancel_approved_order(self):
        res = super(WhIn, self).cancel_approved_order()
        for order in self:
            order.inventory_ids.check_done()

        return res
