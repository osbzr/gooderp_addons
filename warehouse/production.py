# -*- coding: utf-8 -*-

from odoo.osv import osv
from utils import inherits, inherits_after, \
    create_name, safe_division, create_origin
import odoo.addons.decimal_precision as dp
from itertools import islice
from odoo import models, fields, api
from odoo.exceptions import UserError

class wh_assembly(models.Model):
    _name = 'wh.assembly'
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    move_id = fields.Many2one(
        'wh.move', u'移库单', required=True, index=True, ondelete='cascade',
        help=u'组装单对应的移库单')
    bom_id = fields.Many2one(
        'wh.bom', u'模板', domain=[('type', '=', 'assembly')],
        context={'type': 'assembly'}, ondelete='restrict',
        help=u'组装单对应的模板')
    fee = fields.Float(
        u'组装费用', digits=dp.get_precision('Amount'),
        help=u'组装单对应的组装费用，组装费用+组装行入库成本作为子件的出库成本')
    is_many_to_many_combinations = fields.Boolean(u'专家模式', default=False, help="通用情况是一对多的组合,当为False时\
                            视图只能选则一个产品作为组合件,(选择模板后)此时选择数量会更改子件的数量,当为True时则可选择多个组合件,此时组合件产品数量\
                            不会自动影响子件的数量")
    goods_id = fields.Many2one('goods', string=u'组合件产品')
    goods_qty = fields.Float(u'组合件数量', default=1, digits=dp.get_precision('Quantity'), help="(选择使用模板后)当更改这个数量的时候后\
                                                                                              自动的改变相应的子件的数量")
    voucher_id = fields.Many2one('voucher',string='凭证号')

    def apportion_cost(self, cost):
        for assembly in self:
            if not assembly.line_in_ids:
                continue

            collects = []
            ignore_move = [line.id for line in assembly.line_in_ids]
            for parent in assembly.line_in_ids:
                collects.append((
                    parent, parent.goods_id.get_suggested_cost_by_warehouse(
                        parent.warehouse_dest_id, parent.goods_qty,
                        lot_id=parent.lot_id,
                        attribute=parent.attribute_id,
                        ignore_move=ignore_move)[0]))

            amount_total, collect_parent_cost = sum(
                collect[1] for collect in collects), 0
            for parent, amount in islice(collects, 0, len(collects) - 1):
                parent_cost = safe_division(amount, amount_total) * cost
                collect_parent_cost += parent_cost
                parent.write({
                        'cost_unit': safe_division(
                            parent_cost, parent.goods_qty),
                        'cost': parent_cost,
                    })

            # 最后一行数据使用总金额减去已经消耗的金额来计算
            last_parent_cost = cost - collect_parent_cost
            collects[-1][0].write({
                    'cost_unit': safe_division(
                        last_parent_cost, collects[-1][0].goods_qty),
                    'cost': last_parent_cost,
                })

        return True

    def update_parent_cost(self):
        for assembly in self:
            cost = sum(child.cost for child in assembly.line_out_ids) + \
                assembly.fee

            assembly.apportion_cost(cost)

        return True

    @api.onchange('goods_id')
    def onchange_goods_id(self):
        if self.goods_id:
            self.line_in_ids=[{'goods_id': self.goods_id.id, 'product_uos_qty': 1, 'goods_qty': 1,
                             'uom_id': self.goods_id.uom_id.id,'uos_id':self.goods_id.uos_id.id}]

    @api.onchange('goods_qty')
    def onchange_goods_qty(self):
        """
        改变产品数量时(wh_assembly 中的goods_qty) 根据模板的 数量的比例及成本价的计算
        算出新的组合件或者子件的 数量 (line.goods_qty / parent_line_goods_qty * self.goods_qty
        line.goods_qty 子件产品数量
        parent_line_goods_qty 模板组合件产品数量
        self.goods_qty 所要的组合件的产品数量
        line.goods_qty /parent_line_goods_qty 得出子件和组合件的比例
        line.goods_qty / parent_line_goods_qty * self.goods_qty 得出子件实际的数量的数量
        )
        :return:line_out_ids ,line_in_ids
        """
        line_out_ids, line_in_ids = [], []
        warehouse_id = self.env['warehouse'].search(
            [('type', '=', 'stock')], limit=1)
        if self.bom_id:
            line_in_ids = [{'goods_id': line.goods_id.id,
                               'warehouse_id': self.env['warehouse'].get_warehouse_by_type(
                                   'production').id,
                               'warehouse_dest_id': warehouse_id.id,
                               'uom_id': line.goods_id.uom_id.id,
                               'goods_qty': self.goods_qty,
                               'goods_uos_qty': self.goods_qty / line.goods_id.conversion,
                               'uos_id': line.goods_id.uos_id.id,
                           } for line in self.bom_id.line_parent_ids]
            parent_line_goods_qty = self.bom_id.line_parent_ids[0].goods_qty
            for line in self.bom_id.line_child_ids:
                cost, cost_unit = line.goods_id. \
                    get_suggested_cost_by_warehouse(
                    warehouse_id[0], line.goods_qty / parent_line_goods_qty * self.goods_qty)
                local_goods_qty = line.goods_qty / parent_line_goods_qty * self.goods_qty
                line_out_ids.append({
                    'goods_id': line.goods_id.id,
                    'warehouse_id': warehouse_id.id,
                    'warehouse_dest_id': self.env[
                        'warehouse'].get_warehouse_by_type('production'),
                    'uom_id': line.goods_id.uom_id.id,
                    'goods_qty':  local_goods_qty,
                    'cost_unit': cost_unit,
                    'cost': cost,
                    'goods_uos_qty': local_goods_qty/ line.goods_id.conversion,
                    'uos_id': line.goods_id.uos_id.id,
                })
            self.line_in_ids = False
            self.line_out_ids = False
            self.line_out_ids = line_out_ids
            self.line_in_ids = line_in_ids
        elif self.line_in_ids:
            self.line_in_ids[0].goods_qty = self.goods_qty

    @api.one
    def check_parent_length(self):
        if not len(self.line_in_ids) or not len(self.line_out_ids):
            raise UserError(u'组合件和子件的产品必须存在')

    def create_voucher_line(self, data):
        return [self.env['voucher.line'].create(data_line) for data_line in data]

    def create_vourcher_line_data(self, assembly, voucher_row):
        line_out_data, line_in_data = [], []
        for line_out in assembly.line_out_ids:
            account_id = self.env.ref('finance.account_cost').id
            line_out_data.append({'credit': line_out.cost,
                                         'goods_id': line_out.goods_id.id,
                                         'voucher_id': voucher_row.id,
                                         'account_id': account_id,
                                         'name': u'组合单 原料'})
        for line_in in assembly.line_in_ids:
            account_id = line_in.goods_id.category_id.account_id.id
            line_in_data.append({'debit': line_in.cost,
                                        'goods_id':line_in.goods_id.id,
                                        'voucher_id': voucher_row.id,
                                        'account_id': account_id,
                                        'name': u'组合单 成品'})
        return line_out_data + line_in_data

    def wh_assembly_create_voucher_line(self, assembly, voucher_row):
        voucher_line_data = []
        if assembly.fee:
            account_row = assembly.create_uid.company_id.operating_cost_account_id
            voucher_line_data.append({'name': '组装费用', 'account_id': account_row.id,
                                      'credit': assembly.fee, 'voucher_id': voucher_row.id})
        voucher_line_data += self.create_vourcher_line_data(assembly, voucher_row)
        self.create_voucher_line(voucher_line_data)

    def wh_assembly_create_voucher(self):
        for assembly in self:
            if not assembly.fee:
                return True
            voucher_row = self.env['voucher'].create({'date': fields.Datetime.now()})
            self.wh_assembly_create_voucher_line(assembly, voucher_row)
            assembly.voucher_id = voucher_row.id
            voucher_row.voucher_done()

    @api.multi
    @inherits_after(res_back=False)
    def approve_order(self):
        self.check_parent_length()
        self.wh_assembly_create_voucher()
        return self.update_parent_cost()

    @api.multi
    @inherits()
    def cancel_approved_order(self):
        for assembly in self:
            if assembly.voucher_id:
                assembly.voucher_id.voucher_draft()
                assembly.voucher_id.unlink()
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

    @api.onchange('bom_id')
    def onchange_bom(self):
        line_out_ids, line_in_ids = [], []
        domain = {}
        # TODO
        warehouse_id = self.env['warehouse'].search(
            [('type', '=', 'stock')], limit=1)
        if self.bom_id:
            line_in_ids = [{
                'goods_id': line.goods_id.id,
                'warehouse_id': self.env['warehouse'].get_warehouse_by_type(
                    'production').id,
                'warehouse_dest_id': warehouse_id.id,
                'uom_id': line.goods_id.uom_id.id,
                'goods_qty': line.goods_qty,
                'goods_uos_qty': line.goods_qty / line.goods_id.conversion,
                'uos_id': line.goods_id.uos_id.id,
            } for line in self.bom_id.line_parent_ids]

            for line in self.bom_id.line_child_ids:
                cost, cost_unit = line.goods_id. \
                    get_suggested_cost_by_warehouse(
                        warehouse_id[0], line.goods_qty)
                line_out_ids.append({
                        'goods_id': line.goods_id.id,
                        'warehouse_id': warehouse_id.id,
                        'warehouse_dest_id': self.env[
                            'warehouse'].get_warehouse_by_type('production').id,
                        'uom_id': line.goods_id.uom_id.id,
                        'goods_qty': line.goods_qty,
                        'cost_unit': cost_unit,
                        'cost': cost,
                        'goods_uos_qty': self.goods_qty / line.goods_id.conversion,
                        'uos_id': line.goods_id.uos_id.id,
                    })
            self.line_in_ids = False
            self.line_out_ids = False
        else:
            self.goods_qty=1

        if len(line_in_ids) == 1:
            """当模板中只有一个组合件的时候,默认本单据只有一个组合件 设置is_many_to_many_combinations 为False
                使试图只能在 many2one中选择一个产品(并且只能选择在模板中的产品),并且回写数量"""
            self.is_many_to_many_combinations = False
            self.goods_qty = line_in_ids[0].get("goods_qty")
            self.goods_id = line_in_ids[0].get("goods_id")
            domain = {'goods_id': [('id', '=', self.goods_id.id)]}

        elif len(line_in_ids) > 1:
            self.is_many_to_many_combinations = True
        if line_out_ids:
            self.line_out_ids = line_out_ids
        # /odoo-china/odoo/fields.py[1664]行添加的参数
        # 调用self.line_in_ids = line_in_ids的时候，此时会为其额外添加一个参数(6, 0, [])
        # 在write函数的源代码中，会直接使用原表/odoo-china/odoo/osv/fields.py(839)来删除所有数据
        # 此时，上一步赋值的数据将会被直接删除，（不确定是bug，还是特性）
        if line_in_ids:
            self.line_in_ids = line_in_ids
        return {'domain': domain}


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

                assembly.bom_id.write({
                    'line_parent_ids': line_parent_ids,
                    'line_child_ids': line_child_ids})
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

    move_id = fields.Many2one(
        'wh.move', u'移库单', required=True, index=True, ondelete='cascade',
        help=u'拆卸单对应的移库单')
    bom_id = fields.Many2one(
        'wh.bom', u'模板', domain=[('type', '=', 'disassembly')],
        context={'type': 'disassembly'}, ondelete='restrict',
        help=u'拆卸单对应的模板')
    fee = fields.Float(
        u'拆卸费用', digits=dp.get_precision('Amount'),
        help=u'拆卸单对应的拆卸费用, 拆卸费用+拆卸行出库成本作为子件的入库成本')
    is_many_to_many_combinations = fields.Boolean(u'专家模式', default=False,help="通用情况是一对多的组合,当为False时\
                            视图只能选则一个产品作为组合件,(选择模板后)此时选择数量会更改子件的数量,当为True时则可选择多个组合件,此时组合件产品数量\
                            不会自动影响子件的数量")
    goods_id = fields.Many2one('goods', string=u'组合件产品')
    goods_qty = fields.Float(u'组合件数量',default=1, digits=dp.get_precision('Quantity'),help="(选择使用模板后)当更改这个数量的时候后\
                                                                                          自动的改变相应的子件的数量")
    voucher_id = fields.Many2one('voucher', string='凭证号')

    def apportion_cost(self, cost):
        for assembly in self:
            if not assembly.line_in_ids:
                continue

            collects = []
            ignore_move = [line.id for line in assembly.line_in_ids]
            for child in assembly.line_in_ids:
                collects.append((
                    child, child.goods_id.get_suggested_cost_by_warehouse(
                        child.warehouse_dest_id, child.goods_qty,
                        lot_id=child.lot_id, attribute=child.attribute_id,
                        ignore_move=ignore_move)[0]))

            amount_total, collect_child_cost = \
                sum(collect[1] for collect in collects), 0
            for child, amount in islice(collects, 0, len(collects) - 1):
                child_cost = safe_division(amount, amount_total) * cost
                collect_child_cost += child_cost
                child.write({
                        'cost_unit': safe_division(
                            child_cost, child.goods_qty),
                        'cost': child_cost,
                    })

            # 最后一行数据使用总金额减去已经消耗的金额来计算
            last_child_cost = cost - collect_child_cost
            collects[-1][0].write({
                    'cost_unit': safe_division(
                        last_child_cost, collects[-1][0].goods_qty),
                    'cost': last_child_cost,
                })

        return True

    def update_child_cost(self):
        for assembly in self:
            cost = sum(child.cost for child in assembly.line_out_ids) + \
                assembly.fee

            assembly.apportion_cost(cost)
        return True

    @api.one
    def check_parent_length(self):
        if not len(self.line_in_ids) or not len(self.line_out_ids):
            raise UserError(u'组合件和子件的产品必须存在')

    def create_voucher_line(self, data):
        return [self.env['voucher.line'].create(data_line) for data_line in data]

    def create_vourcher_line_data(self, assembly, voucher_row):
        line_out_data, line_in_data = [], []
        for line_out in assembly.line_out_ids:
            account_id = self.env.ref('finance.account_cost').id
            line_out_data.append({'credit': line_out.cost,
                                         'goods_id': line_out.goods_id.id,
                                         'voucher_id': voucher_row.id,
                                         'account_id': account_id,
                                         'name': u'拆卸单 原料'})
        for line_in in assembly.line_in_ids:
            account_id = line_in.goods_id.category_id.account_id.id
            line_in_data.append({'debit': line_in.cost,
                                        'goods_id':line_in.goods_id.id,
                                        'voucher_id': voucher_row.id,
                                        'account_id': account_id,
                                        'name': u'拆卸单 成品'})
        return line_out_data + line_in_data

    def wh_disassembly_create_voucher_line(self, disassembly, voucher_row):
        voucher_line_data = []
        if disassembly.fee:
            account_row = disassembly.create_uid.company_id.operating_cost_account_id
            voucher_line_data.append({'name': '拆卸费用', 'account_id': account_row.id,
                                      'credit': disassembly.fee, 'voucher_id': voucher_row.id})
        voucher_line_data += self.create_vourcher_line_data(disassembly, voucher_row)
        self.create_voucher_line(voucher_line_data)

    def wh_disassembly_create_voucher(self):
        for disassembly in self:
            if not disassembly.fee:
                return True
            voucher_row = self.env['voucher'].create({'date': fields.Datetime.now()})
            self.wh_disassembly_create_voucher_line(disassembly, voucher_row)
            disassembly.voucher_id = voucher_row.id
            voucher_row.voucher_done()

    @api.multi
    @inherits_after(res_back=False)
    def approve_order(self):
        self.check_parent_length()
        self.wh_disassembly_create_voucher()
        return self.update_child_cost()

    @api.multi
    @inherits()
    def cancel_approved_order(self):
        for disassembly in self:
            if disassembly.voucher_id:
                disassembly.voucher_id.voucher_draft()
                disassembly.voucher_id.unlink()
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

    @api.onchange('goods_id')
    def onchange_goods_id(self):
        if self.goods_id:
            warehouse_id = self.env['warehouse'].search(
                [('type', '=', 'stock')], limit=1)
            self.line_out_ids = [{'goods_id': self.goods_id.id, 'product_uos_qty': 1, 'goods_qty': 1,
                                  'warehouse_id': self.env['warehouse'].get_warehouse_by_type('production').id,
                                  'warehouse_dest_id': warehouse_id.id,
                                  'uom_id': self.goods_id.uom_id.id,
                                  'uos_id': self.goods_id.uos_id.id,
                                  }]

    @api.onchange('goods_qty')
    def onchange_goods_qty(self):
        """
        改变产品数量时(wh_assembly 中的goods_qty) 根据模板的 数量的比例及成本价的计算
        算出新的组合件或者子件的 数量 (line.goods_qty / parent_line_goods_qty * self.goods_qty
        line.goods_qty 子件产品数量
        parent_line_goods_qty 模板组合件产品数量
        self.goods_qty 所要的组合件的产品数量
        line.goods_qty /parent_line_goods_qty 得出子件和组合件的比例
        line.goods_qty / parent_line_goods_qty * self.goods_qty 得出子件实际的数量的数量
        )
        :return:line_out_ids ,line_in_ids
        """
        warehouse_id = self.env['warehouse'].search(
            [('type', '=', 'stock')], limit=1)
        line_out_ids,line_in_ids = [],[]
        parent_line = self.bom_id.line_parent_ids
        if warehouse_id and self.bom_id and parent_line and self.bom_id.line_child_ids:
            cost, cost_unit = parent_line.goods_id \
                 .get_suggested_cost_by_warehouse(
                 warehouse_id, self.goods_qty)

            line_out_ids.append({
                 'goods_id': parent_line.goods_id.id,
                 'warehouse_id': self.env[
                     'warehouse'].get_warehouse_by_type('production').id,
                 'warehouse_dest_id': warehouse_id.id,
                 'uom_id': parent_line.goods_id.uom_id.id,
                 'goods_qty': self.goods_qty,
                 'goods_uos_qty': self.goods_qty/parent_line.goods_id.conversion,
                 'uos_id':parent_line.goods_id.uos_id.id,
                 'cost_unit': cost_unit,
                 'cost': cost,
             })

            line_in_ids = [{
                            'goods_id': line.goods_id.id,
                            'warehouse_id': warehouse_id.id,
                            'warehouse_dest_id': self.env[
                                'warehouse'].get_warehouse_by_type('production').id,
                            'uom_id': line.goods_id.uom_id.id,
                            'goods_qty': line.goods_qty/parent_line.goods_qty*self.goods_qty,
                            'goods_uos_qty': line.goods_qty/parent_line.goods_qty*self.goods_qty/line.goods_id.conversion,
                            'uos_id':line.goods_id.uos_id.id,
                        } for line in self.bom_id.line_child_ids]

            if line_out_ids:
                self.line_out_ids = line_out_ids
            if line_in_ids:
                self.line_in_ids = line_in_ids

        elif self.line_out_ids:
            self.line_out_ids[0].goods_qty = self.goods_qty

    @api.onchange('bom_id')
    def onchange_bom(self):
        line_out_ids, line_in_ids = [], []
        domain = {}
        # TODO
        warehouse_id = self.env['warehouse'].search(
            [('type', '=', 'stock')], limit=1)
        if self.bom_id:
            line_out_ids = []
            for line in self.bom_id.line_parent_ids:
                cost, cost_unit = line.goods_id \
                    .get_suggested_cost_by_warehouse(
                        warehouse_id, line.goods_qty)
                line_out_ids.append({
                        'goods_id': line.goods_id,
                        'warehouse_id': self.env[
                            'warehouse'].get_warehouse_by_type('production').id,
                        'warehouse_dest_id': warehouse_id.id,
                        'uom_id': line.goods_id.uom_id.id,
                        'goods_qty': line.goods_qty,
                        'goods_uos_qty': line.goods_qty/line.goods_id.conversion,
                        'uos_id':line.goods_id.uos_id.id,
                        'cost_unit': cost_unit,
                        'cost': cost,
                    })

            line_in_ids = [{
                'goods_id': line.goods_id.id,
                'warehouse_id': warehouse_id,
                'warehouse_dest_id': self.env[
                    'warehouse'].get_warehouse_by_type('production').id,
                'uom_id': line.goods_id.uom_id.id,
                'goods_qty': line.goods_qty,
                'goods_uos_qty': line.goods_qty/line.goods_id.conversion,
                'uos_id':line.goods_id.uos_id.id,
            } for line in self.bom_id.line_child_ids]

            self.line_in_ids = False
            self.line_out_ids = False
        else:
            self.goods_qty=1
        if len(line_out_ids) == 1 and line_out_ids:
            """当模板中只有一个组合件的时候,默认本单据只有一个组合件 设置is_many_to_many_combinations 为False
             使试图只能在 many2one中选择一个产品(并且只能选择在模板中的产品),并且回写数量"""
            self.is_many_to_many_combinations = ''
            self.goods_qty = line_out_ids[0].get("goods_qty")
            self.goods_id = line_out_ids[0].get("goods_id")
            domain = {'goods_id': [('id', '=', self.goods_id.id)]}

        elif len(line_out_ids) > 1:
            self.is_many_to_many_combinations = True
        if line_out_ids:
            self.line_out_ids = line_out_ids
        if line_in_ids:
            self.line_in_ids = line_in_ids
        return {'domain': domain}



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

                disassembly.bom_id.write({
                    'line_parent_ids': line_parent_ids,
                    'line_child_ids': line_child_ids})
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

    name = fields.Char(u'模板名称',
                       help=u'组装/拆卸模板名称')
    type = fields.Selection(
        BOM_TYPE, u'类型', default=lambda self: self.env.context.get('type'),
        help=u'类型: 组装单、拆卸单')
    line_parent_ids = fields.One2many(
        'wh.bom.line', 'bom_id', u'组合件', domain=[('type', '=', 'parent')],
        context={'type': 'parent'}, copy=True,
        help=u'模板对应的组合件行')
    line_child_ids = fields.One2many(
        'wh.bom.line', 'bom_id', u'子件', domain=[('type', '=', 'child')],
        context={'type': 'child'}, copy=True,
        help=u'模板对应的子件行')


class wh_bom_line(osv.osv):
    _name = 'wh.bom.line'

    BOM_LINE_TYPE = [
        ('parent', u'组合件'),
        ('child', u'子间'),
    ]

    bom_id = fields.Many2one('wh.bom', u'模板', ondelete='cascade',
                             help=u'子件行/组合件行对应的模板')
    type = fields.Selection(
        BOM_LINE_TYPE, u'类型',
        default=lambda self: self.env.context.get('type'),
        help=u'类型: 组合件、子间')
    goods_id = fields.Many2one('goods', u'产品', default=1, ondelete='restrict',
                               help=u'子件行/组合件行上的产品')
    goods_qty = fields.Float(
        u'数量', digits=dp.get_precision('Quantity'),
        help=u'子件行/组合件行上的产品数量')
