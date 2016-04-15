# -*- coding: utf-8 -*-

from openerp.osv import osv
# from openerp.osv import fields
from utils import create_name, safe_division
import openerp.addons.decimal_precision as dp

from openerp import models
from openerp import fields
from openerp import api


class wh_inventory(models.Model):
    _name = 'wh.inventory'
    _order = 'date DESC, id DESC'

    INVENTORY_STATE = [
        ('draft', u'草稿'),
        ('query', u'查询中'),
        ('confirmed', u'待确认盘盈盘亏'),
        ('done', u'完成'),
    ]

    date = fields.Date(u'日期', default=fields.Date.context_today)
    name = fields.Char(u'名称', copy=False, default='/')
    warehouse_id = fields.Many2one('warehouse', u'仓库')
    goods = fields.Char(u'产品')
    uos_not_zero = fields.Boolean(u'辅助数量不为0')
    out_id = fields.Many2one('wh.out', u'盘亏单据', copy=False)
    in_id = fields.Many2one('wh.in', u'盘盈单据', copy=False)
    state = fields.Selection(INVENTORY_STATE, u'状态', copy=False, default='draft')
    line_ids = fields.One2many('wh.inventory.line', 'inventory_id', u'明细', copy=False)
    note = fields.Text(u'备注')

    @api.multi
    def requery_inventory(self):
        self.delete_confirmed_wh()
        self.state = 'query'

    @api.model
    @create_name
    def create(self, vals):
        return super(wh_inventory, self).create(vals)

    @api.multi
    def unlink(self):
        for inventory in self:
            if inventory.state == 'done':
                raise osv.except_osv(u'错误', u'不可以删除一个完成的单据')

            inventory.delete_confirmed_wh()

        return super(wh_inventory, self).unlink()

    def delete_confirmed_wh(self):
        for inventory in self:
            if inventory.state == 'confirmed':
                if (inventory.out_id and inventory.out_id.state == 'done') or (inventory.in_id and inventory.in_id.state == 'done'):
                    raise osv.except_osv(u'错误', u'请先反审核掉相关的盘盈盘亏单据')
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
        out_vals = {
            'type': 'losses',
            'line_out_ids': [],
        }

        for line in out_line:
            out_vals['line_out_ids'].append([0, False, line.get_move_line(wh_type='out')])

        out_id = self.env['wh.out'].create(out_vals)
        inventory.out_id = out_id

    def create_overage_in(self, inventory, in_line):
        in_vals = {
            'type': 'overage',
            'line_in_ids': [],
        }

        for line in in_line:
            in_vals['line_in_ids'].append([0, False, line.get_move_line(wh_type='in')])

        in_id = self.env['wh.in'].create(in_vals)
        inventory.in_id = in_id

    @api.multi
    def generate_inventory(self):
        for inventory in self:
            out_line, in_line = [], []
            for line in inventory.line_ids.filtered(lambda line: line.difference_qty or line.difference_uos_qty):
                if line.difference_qty <= 0 and line.difference_uos_qty <= 0:
                    out_line.append(line)
                elif line.difference_qty >= 0 and line.difference_uos_qty >= 0:
                    in_line.append(line)
                else:
                    raise osv.except_osv(u'错误',
                        u'产品"%s"行上盘盈盘亏数量与辅助单位的盘盈盘亏数量盈亏方向不一致' % line.goods_id.name)

            if out_line:
                self.create_losses_out(inventory, out_line)

            if in_line:
                self.create_overage_in(inventory, in_line)

            if out_line or in_line:
                inventory.state = 'confirmed'

        return True

    def get_line_detail(self, uos_zero=False):
        for inventory in self:
            if uos_zero:
                remaining_text = '(line.qty_remaining > 0 OR line.uos_qty_remaining > 0)'
            else:
                remaining_text = 'line.qty_remaining > 0'

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

                WHERE {}
                  AND wh.type = 'stock'
                  AND line.state = 'done'
                  %s

                GROUP BY wh.id, line.lot, line.attribute_id, goods.id, uom.id, uos.id
            '''.format(remaining_text)

            extra_text = ''
            if inventory.warehouse_id:
                extra_text += ' AND wh.id = %s' % inventory.warehouse_id.id

            if inventory.goods:
                extra_text += " AND goods.name ILIKE '%%%s%%' " % inventory.goods

            inventory.env.cr.execute(sql_text % extra_text)
            return inventory.env.cr.dictfetchall()

    @api.multi
    def query_inventory(self):
        line_obj = self.env['wh.inventory.line']
        for inventory in self:
            inventory.delete_line()
            line_ids = inventory.get_line_detail(inventory.uos_not_zero)

            for line in line_ids:
                line_obj.create({
                        'inventory_id': inventory.id,
                        'warehouse_id': line.get('warehouse_id'),
                        'goods_id': line.get('goods_id'),
                        'attribute_id': line.get('attribute_id'),
                        'lot': line.get('lot'),
                        'uom_id': line.get('uom_id'),
                        'uos_id': line.get('uos_id'),
                        'real_qty': line.get('qty'),
                        'real_uos_qty': line.get('uos_qty'),
                        'inventory_qty': line.get('qty'),
                        'inventory_uos_qty': line.get('uos_qty'),
                    })

            if line_ids:
                inventory.state = 'query'

        return True


class wh_inventory_line(models.Model):
    _name = 'wh.inventory.line'

    LOT_TYPE = [
        ('out', u'出库'),
        ('in', u'入库'),
        ('nothing', u'不做处理'),
    ]

    inventory_id = fields.Many2one('wh.inventory', u'盘点', ondelete='cascade')
    warehouse_id = fields.Many2one('warehouse', u'仓库')
    goods_id = fields.Many2one('goods', u'产品')
    attribute_id = fields.Many2one('attribute', u'属性')
    using_batch = fields.Boolean(related='goods_id.using_batch', string=u'批号管理')
    force_batch_one = fields.Boolean(related='goods_id.force_batch_one', string=u'每批号数量为1')
    lot = fields.Char(u'批号')
    new_lot = fields.Char(u'盘盈批号')
    new_lot_id = fields.Many2one('wh.move.line', u'盘亏批号')
    lot_type = fields.Selection(LOT_TYPE, u'批号类型', default='nothing')
    uom_id = fields.Many2one('uom', u'单位')
    uos_id = fields.Many2one('uom', u'辅助单位')
    real_qty = fields.Float(u'系统库存', digits_compute=dp.get_precision('Goods Quantity'))
    real_uos_qty = fields.Float(u'系统辅助单位库存', digits_compute=dp.get_precision('Goods Quantity'))
    inventory_qty = fields.Float(u'盘点库存', digits_compute=dp.get_precision('Goods Quantity'))
    inventory_uos_qty = fields.Float(u'盘点辅助单位库存', digits_compute=dp.get_precision('Goods Quantity'))
    difference_qty = fields.Float(u'盘盈盘亏', digits_compute=dp.get_precision('Goods Quantity'))
    difference_uos_qty = fields.Float(u'辅助单位盘盈盘亏', digits_compute=dp.get_precision('Goods Quantity'))

    def check_difference_identical(self):
        if self.difference_qty * self.difference_uos_qty < 0:
            self.inventory_qty = self.real_qty
            self.inventory_uos_qty = self.real_uos_qty

            return {'warning': {
                'title': u'错误',
                'message': u'盘盈盘亏数量应该与辅助单位的盘盈盘亏数量盈亏方向一致',
            }}

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
        self.difference_qty = self.inventory_qty - self.real_qty
        self.difference_uos_qty = self.inventory_uos_qty - self.real_uos_qty

        if self.goods_id and self.goods_id.using_batch:
            if self.goods_id.force_batch_one and self.difference_qty:
                flag = self.difference_qty > 0 and 1 or -1
                if abs(self.difference_qty) != 1:
                    self.line_role_back()
                    return {'warning': {
                        'title': u'警告',
                        'message': u'产品上设置了序号为1，此时一次只能盘亏或盘盈一个产品数量',
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

    @api.one
    @api.onchange('inventory_uos_qty')
    def onchange_uos_qty(self):
        self.inventory_qty = self.goods_id.conversion_unit(self.inventory_uos_qty)

    def get_move_line(self, wh_type='in', context=None):
        inventory_warehouse = self.env['warehouse'].get_warehouse_by_type('inventory')
        for inventory in self:

            cost, cost_unit = inventory.goods_id.get_suggested_cost_by_warehouse(
                inventory.warehouse_id, abs(inventory.difference_qty),
                lot_id=inventory.new_lot_id, attribute=inventory.attribute_id)

            return {
                'warehouse_id': wh_type == 'out' and inventory.warehouse_id.id or inventory_warehouse.id,
                'warehouse_dest_id': wh_type == 'in' and inventory.warehouse_id.id or inventory_warehouse.id,
                'lot': inventory.new_lot,
                'lot_id': inventory.new_lot_id.id,
                'goods_id': inventory.goods_id.id,
                'attribute_id': inventory.attribute_id.id,
                'uom_id': inventory.uom_id.id,
                'uos_id': inventory.uos_id.id,
                'goods_qty': abs(inventory.difference_qty),
                'goods_uos_qty': abs(inventory.difference_uos_qty),
                'cost_unit': cost_unit,
                'cost': cost,
            }


class wh_out(models.Model):
    _inherit = 'wh.out'

    inventory_ids = fields.One2many('wh.inventory', 'out_id', u'盘点单')

    @api.multi
    def approve_order(self):
        res = super(wh_out, self).approve_order()
        for order in self:
            order.inventory_ids.check_done()

        return res


class wh_in(models.Model):
    _inherit = 'wh.in'

    inventory_ids = fields.One2many('wh.inventory', 'in_id', u'盘点单')

    @api.multi
    def approve_order(self):
        res = super(wh_in, self).approve_order()
        for order in self:
            order.inventory_ids.check_done()

        return res
