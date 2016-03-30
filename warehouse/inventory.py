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
    zero_inventory = fields.Boolean(u'零库存')
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
            for line in (line for line in inventory.line_ids if line.difference_qty):
                if line.difference_qty < 0:
                    out_line.append(line)
                else:
                    in_line.append(line)

            if out_line:
                self.create_losses_out(inventory, out_line)

            if in_line:
                self.create_overage_in(inventory, in_line)

            if out_line or in_line:
                inventory.state = 'confirmed'

        return True

    def get_line_detail(self):
        for inventory in self:
            sql_text = '''
                SELECT wh.id as warehouse_id,
                       goods.id as goods_id,
                       uom.id as uom_id,
                       sum(line.qty_remaining) as qty

                FROM wh_move_line line
                LEFT JOIN goods goods ON line.goods_id = goods.id
                    LEFT JOIN uom uom ON goods.uom_id = uom.id
                LEFT JOIN warehouse wh ON line.warehouse_dest_id = wh.id

                WHERE line.qty_remaining > 0
                  AND wh.type = 'stock'
                  AND line.state = 'done'
                  %s

                GROUP BY wh.id, goods.id, uom.id
            '''

            extra_text = ''
            # TODO @zzx 可能需要添加一种全部仓库的判断
            if inventory.warehouse_id:
                extra_text += ' AND wh.id = %s' % inventory.warehouse_id.id

            if inventory.goods:
                extra_text += " AND goods.name ILIKE '%%%s%%' " % inventory.goods

            inventory.env.cr.execute(sql_text % extra_text)
            return inventory.env.cr.dictfetchall()

    def get_zero_inventory(self, exist_goods_ids):
        for inventory in self:
            domain = inventory.goods and [('name', 'ilike', '%%%s%%' % inventory.goods)] or []
            zero_goods = self.env['goods'].search(domain)

            res = []
            temp_warehouse = self.env['warehouse'].search([('type', '=', 'stock')], limit=1)
            for goods in zero_goods.filtered(lambda goods: goods.id not in exist_goods_ids):
                res.append({
                        # 'warehouse_id': goods.main_warehouse_id.id, TODO
                        'warehouse_id': temp_warehouse[0].id,
                        'goods_id': goods.id,
                        'uom_id': goods.uom_id.id,
                        'qty': 0,
                    })

            return res

    @api.multi
    def query_inventory(self):
        line_obj = self.env['wh.inventory.line']
        for inventory in self:
            inventory.delete_line()
            line_ids = inventory.get_line_detail()

            if inventory.zero_inventory:
                line_ids.extend(inventory.get_zero_inventory([line.get('goods_id') for line in line_ids]))

            for line in line_ids:
                line_obj.create({
                        'inventory_id': inventory.id,
                        'warehouse_id': line.get('warehouse_id'),
                        'goods_id': line.get('goods_id'),
                        'uom_id': line.get('uom_id'),
                        'real_qty': line.get('qty'),
                    })

            if line_ids:
                inventory.state = 'query'

        return True


class wh_inventory_line(models.Model):
    _name = 'wh.inventory.line'

    inventory_id = fields.Many2one('wh.inventory', u'盘点', ondelete='cascade')
    warehouse_id = fields.Many2one('warehouse', u'仓库')
    goods_id = fields.Many2one('goods', u'产品')
    uom_id = fields.Many2one('uom', u'单位')
    real_qty = fields.Float(u'系统库存', digits_compute=dp.get_precision('Goods Quantity'))
    inventory_qty = fields.Float(u'盘点库存', digits_compute=dp.get_precision('Goods Quantity'))
    difference_qty = fields.Float(u'盘盈盘亏', digits_compute=dp.get_precision('Goods Quantity'))

    @api.one
    @api.onchange('real_qty', 'inventory_qty')
    def onchange_qty(self):
        self.difference_qty = self.inventory_qty - self.real_qty

    def get_move_line(self, wh_type='in', context=None):
        inventory_warehouse = self.env['warehouse'].get_warehouse_by_type('inventory')
        for inventory in self:

            subtotal, matching_qty = inventory.goods_id.get_suggested_cost_by_warehouse(
                inventory.warehouse_id, abs(inventory.difference_qty))
            return {
                'warehouse_id': wh_type == 'out' and inventory.warehouse_id.id or inventory_warehouse.id,
                'warehouse_dest_id': wh_type == 'in' and inventory.warehouse_id.id or inventory_warehouse.id,
                'goods_id': inventory.goods_id.id,
                'uom_id': inventory.uom_id.id,
                'goods_qty': abs(inventory.difference_qty),
                'price': safe_division(subtotal, matching_qty),
                'subtotal': subtotal,
            }


class wh_out(models.Model):
    _inherit = 'wh.out'

    inventory_ids = fields.One2many('wh.inventory', 'out_id', u'盘点单')

    @api.multi
    def approve_order(self):
        res = super(wh_out, self).approve_order()
        self.inventory_ids.check_done()

        return res


class wh_in(models.Model):
    _inherit = 'wh.in'

    inventory_ids = fields.One2many('wh.inventory', 'in_id', u'盘点单')

    @api.multi
    def approve_order(self):
        res = super(wh_in, self).approve_order()
        self.inventory_ids.check_done()

        return res
