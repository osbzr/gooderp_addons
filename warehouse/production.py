# -*- coding: utf-8 -*-

from openerp.osv import osv
from utils import inherits, inherits_after, create_name, safe_division, create_origin
import openerp.addons.decimal_precision as dp
from itertools import islice
from openerp import models, fields, api


class wh_assembly(models.Model):
    _name = 'wh.assembly'
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade')
    bom_id = fields.Many2one('wh.bom', u'模板', domain=[('type', '=', 'assembly')], context={'type': 'assembly'})
    fee = fields.Float(u'组装费用', digits_compute=dp.get_precision('Accounting'))

    def apportion_cost(self, cost):
        for assembly in self:
            if not assembly.line_in_ids:
                continue

            collects = []
            ignore_move = [line.id for line in assembly.line_in_ids]
            for parent in assembly.line_in_ids:
                collects.append((parent, parent.goods_id.get_suggested_cost_by_warehouse(
                    parent.warehouse_dest_id, parent.goods_qty, lot_id=parent.lot_id,
                    attribute=parent.attribute_id, ignore_move=ignore_move)[0]))

            amount_total, collect_parent_cost = sum(collect[1] for collect in collects), 0
            for parent, amount in islice(collects, 0, len(collects) - 1):
                parent_cost = safe_division(amount, amount_total) * cost
                collect_parent_cost += parent_cost
                parent.write({
                        'cost_unit': safe_division(parent_cost, parent.goods_qty),
                        'cost': parent_cost,
                    })

            # 最后一行数据使用总金额减去已经消耗的金额来计算
            last_parent_cost = cost - collect_parent_cost
            collects[-1][0].write({
                    'cost_unit': safe_division(last_parent_cost, collects[-1][0].goods_qty),
                    'cost': last_parent_cost,
                })

        return True

    def update_parent_cost(self):
        for assembly in self:
            cost = sum(child.cost for child in assembly.line_out_ids) + assembly.fee

            assembly.apportion_cost(cost)

        return True

    @api.one
    def check_parent_length(self):
        if not len(self.line_in_ids) or not len(self.line_out_ids):
            raise osv.except_osv(u'错误', u'组合件和子件的产品必须存在')

    @api.multi
    @inherits_after(res_back=False)
    def approve_order(self):
        self.check_parent_length()
        return self.update_parent_cost()

    @api.multi
    @inherits()
    def cancel_approved_order(self):
        return True

    @api.multi
    @inherits_after()
    def unlink(self):
        return super(wh_assembly, self).unlink()

    @api.model
    @create_name
    @create_origin
    def create(self, vals):
        self = super(wh_assembly, self).create(vals)
        self.update_parent_cost()

        return self

    @api.multi
    def write(self, vals):
        res = super(wh_assembly, self).write(vals)
        self.update_parent_cost()

        return res

    @api.one
    @api.onchange('bom_id')
    def onchange_bom(self):
        line_out_ids, line_in_ids = [], []

        # TODO
        warehouse_id = self.env['warehouse'].search([('type', '=', 'stock')], limit=1)
        if self.bom_id:
            line_in_ids = [{
                'goods_id': line.goods_id,
                'warehouse_id': self.env['warehouse'].get_warehouse_by_type('production'),
                'warehouse_dest_id': warehouse_id,
                'uom_id': line.goods_id.uom_id,
                'goods_qty': line.goods_qty,
            } for line in self.bom_id.line_parent_ids]

            for line in self.bom_id.line_child_ids:
                cost, cost_unit = line.goods_id.get_suggested_cost_by_warehouse(
                    warehouse_id[0], line.goods_qty)

                line_out_ids.append({
                        'goods_id': line.goods_id,
                        'warehouse_id': warehouse_id,
                        'warehouse_dest_id': self.env['warehouse'].get_warehouse_by_type('production'),
                        'uom_id': line.goods_id.uom_id,
                        'goods_qty': line.goods_qty,
                        'cost_unit': cost_unit,
                        'cost': cost,
                    })

            self.line_in_ids = False
            self.line_out_ids = False

        self.line_out_ids = line_out_ids
        # /openerp-china/openerp/fields.py[1664]行添加的参数
        # 调用self.line_in_ids = line_in_ids的时候，此时会为其额外添加一个参数(6, 0, [])
        # 在write函数的源代码中，会直接使用原表/openerp-china/openerp/osv/fields.py(839)来删除所有数据
        # 此时，上一步赋值的数据将会被直接删除，（不确定是bug，还是特性）
        self.line_in_ids = line_in_ids

    @api.multi
    def update_bom(self):
        for assembly in self:
            if assembly.bom_id:
                return assembly.save_bom()
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'save.bom.memory',
                    'view_mode': 'form',
                    'target': 'new',
                }

    def save_bom(self, name=''):
        for assembly in self:
            line_parent_ids = [[0, False, {
                'goods_id': line.goods_id.id,
                'goods_qty': line.goods_qty,
            }] for line in assembly.line_in_ids]

            line_child_ids = [[0, False, {
                'goods_id': line.goods_id.id,
                'goods_qty': line.goods_qty,
            }] for line in assembly.line_out_ids]

            if assembly.bom_id:
                assembly.bom_id.line_parent_ids.unlink()
                assembly.bom_id.line_child_ids.unlink()

                assembly.bom_id.write({'line_parent_ids': line_parent_ids, 'line_child_ids': line_child_ids})
            else:
                bom_id = self.env['wh.bom'].create({
                        'name': name,
                        'type': 'assembly',
                        'line_parent_ids': line_parent_ids,
                        'line_child_ids': line_child_ids,
                    })
                assembly.bom_id = bom_id

        return True


class wh_disassembly(models.Model):
    _name = 'wh.disassembly'
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade')
    bom_id = fields.Many2one('wh.bom', u'模板', domain=[('type', '=', 'disassembly')], context={'type': 'disassembly'})
    fee = fields.Float(u'拆卸费用', digits_compute=dp.get_precision('Accounting'))

    def apportion_cost(self, cost):
        for assembly in self:
            if not assembly.line_in_ids:
                continue

            collects = []
            ignore_move = [line.id for line in assembly.line_in_ids]
            for child in assembly.line_in_ids:
                collects.append((child, child.goods_id.get_suggested_cost_by_warehouse(
                    child.warehouse_dest_id, child.goods_qty, lot_id=child.lot_id,
                    attribute=child.attribute_id, ignore_move=ignore_move)[0]))

            amount_total, collect_child_cost = sum(collect[1] for collect in collects), 0
            for child, amount in islice(collects, 0, len(collects) - 1):
                child_cost = safe_division(amount, amount_total) * cost
                collect_child_cost += child_cost
                child.write({
                        'cost_unit': safe_division(child_cost, child.goods_qty),
                        'cost': child_cost,
                    })

            # 最后一行数据使用总金额减去已经消耗的金额来计算
            last_child_cost = cost - collect_child_cost
            collects[-1][0].write({
                    'cost_unit': safe_division(last_child_cost, collects[-1][0].goods_qty),
                    'cost': last_child_cost,
                })

        return True

    def update_child_cost(self):
        for assembly in self:
            cost = sum(child.cost for child in assembly.line_out_ids) + assembly.fee

            assembly.apportion_cost(cost)
        return True

    @api.one
    def check_parent_length(self):
        if not len(self.line_in_ids) or not len(self.line_out_ids):
            raise osv.except_osv(u'错误', u'组合件和子件的产品必须存在')

    @api.multi
    @inherits_after(res_back=False)
    def approve_order(self):
        self.check_parent_length()
        return self.update_child_cost()

    @api.multi
    @inherits()
    def cancel_approved_order(self):
        return True

    @api.multi
    @inherits_after()
    def unlink(self):
        return super(wh_disassembly, self).unlink()

    @api.model
    @create_name
    @create_origin
    def create(self, vals):
        self = super(wh_disassembly, self).create(vals)
        self.update_child_cost()

        return self

    @api.multi
    def write(self, vals):
        res = super(wh_disassembly, self).write(vals)
        self.update_child_cost()

        return res

    @api.one
    @api.onchange('bom_id')
    def onchange_bom(self):
        line_out_ids, line_in_ids = [], []
        # TODO
        warehouse_id = self.env['warehouse'].search([('type', '=', 'stock')], limit=1)
        if self.bom_id:
            line_out_ids = []
            for line in self.bom_id.line_parent_ids:
                cost, cost_unit = line.goods_id.get_suggested_cost_by_warehouse(
                    warehouse_id, line.goods_qty)
                line_out_ids.append({
                        'goods_id': line.goods_id,
                        'warehouse_id': self.env['warehouse'].get_warehouse_by_type('production'),
                        'warehouse_dest_id': warehouse_id,
                        'uom_id': line.goods_id.uom_id,
                        'goods_qty': line.goods_qty,
                        'cost_unit': cost_unit,
                        'cost': cost,
                    })

            line_in_ids = [{
                'goods_id': line.goods_id,
                'warehouse_id': warehouse_id,
                'warehouse_dest_id': self.env['warehouse'].get_warehouse_by_type('production'),
                'uom_id': line.goods_id.uom_id,
                'goods_qty': line.goods_qty,
            } for line in self.bom_id.line_child_ids]

            self.line_in_ids = False
            self.line_out_ids = False

        self.line_out_ids = line_out_ids or False
        self.line_in_ids = line_in_ids or False

    @api.multi
    def update_bom(self):
        for disassembly in self:
            if disassembly.bom_id:
                return disassembly.save_bom()
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'save.bom.memory',
                    'view_mode': 'form',
                    'target': 'new',
                }

    def save_bom(self, name=''):
        for disassembly in self:
            line_child_ids = [[0, False, {
                'goods_id': line.goods_id.id,
                'goods_qty': line.goods_qty,
            }] for line in disassembly.line_in_ids]

            line_parent_ids = [[0, False, {
                'goods_id': line.goods_id.id,
                'goods_qty': line.goods_qty,
            }] for line in disassembly.line_out_ids]

            if disassembly.bom_id:
                disassembly.bom_id.line_parent_ids.unlink()
                disassembly.bom_id.line_child_ids.unlink()

                disassembly.bom_id.write({'line_parent_ids': line_parent_ids, 'line_child_ids': line_child_ids})
            else:
                bom_id = self.env['wh.bom'].create({
                        'name': name,
                        'type': 'disassembly',
                        'line_parent_ids': line_parent_ids,
                        'line_child_ids': line_child_ids,
                    })
                disassembly.bom_id = bom_id

        return True


class wh_bom(osv.osv):
    _name = 'wh.bom'

    BOM_TYPE = [
        ('assembly', u'组装单'),
        ('disassembly', u'拆卸单'),
    ]

    name = fields.Char(u'模板名称')
    type = fields.Selection(BOM_TYPE, u'类型', default=lambda self: self.env.context.get('type'))
    line_parent_ids = fields.One2many('wh.bom.line', 'bom_id', u'组合件', domain=[('type', '=', 'parent')], context={'type': 'parent'}, copy=True)
    line_child_ids = fields.One2many('wh.bom.line', 'bom_id', u'子件', domain=[('type', '=', 'child')], context={'type': 'child'}, copy=True)


class wh_bom_line(osv.osv):
    _name = 'wh.bom.line'

    BOM_LINE_TYPE = [
        ('parent', u'组合件'),
        ('child', u'子间'),
    ]

    bom_id = fields.Many2one('wh.bom', u'模板')
    type = fields.Selection(BOM_LINE_TYPE, u'类型', default=lambda self: self.env.context.get('type'))
    goods_id = fields.Many2one('goods', u'产品', default=1)
    goods_qty = fields.Float(u'数量', digits_compute=dp.get_precision('Goods Quantity'))
