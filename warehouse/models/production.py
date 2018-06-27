# -*- coding: utf-8 -*-

from odoo.osv import osv
from utils import inherits, inherits_after, \
    create_name, safe_division, create_origin
import odoo.addons.decimal_precision as dp
from itertools import islice
from odoo import models, fields, api
from odoo.exceptions import UserError


class WhAssembly(models.Model):
    _name = 'wh.assembly'
    _description = u'组装单'
    _inherit = ['mail.thread']
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    state = fields.Selection([('draft', u'草稿'),
                              ('feeding', u'已发料'),
                              ('done', u'完成'),
                              ('cancel', u'已作废')],
                             u'状态', copy=False, default='draft',
                             index=True,
                             help=u'组装单状态标识，新建时状态为草稿；发料后状态为已发料，可以多次投料；成品入库后状态为完成。')
    move_id = fields.Many2one(
        'wh.move', u'移库单', required=True, index=True, ondelete='cascade',
        help=u'组装单对应的移库单')
    bom_id = fields.Many2one(
        'wh.bom', u'物料清单', domain=[('type', '=', 'assembly')],
        context={'type': 'assembly'}, ondelete='restrict',
        readonly=True,
        states={'draft': [('readonly', False)], 'feeding': [
            ('readonly', False)]},
        help=u'组装单对应的物料清单')
    fee = fields.Float(
        u'组装费用', digits=dp.get_precision('Amount'),
        readonly=True,
        states={'draft': [('readonly', False)], 'feeding': [
            ('readonly', False)]},
        help=u'组装单对应的组装费用，组装费用+组装行入库成本作为子件的出库成本')
    is_many_to_many_combinations = fields.Boolean(u'专家模式', default=False, help=u"通用情况是一对多的组合,当为False时\
                            视图只能选则一个商品作为组合件,(选择物料清单后)此时选择数量会更改子件的数量,当为True时则可选择多个组合件,此时组合件商品数量\
                            不会自动影响子件的数量")
    goods_id = fields.Many2one('goods', string=u'组合件商品',
                               readonly=True,
                               states={'draft': [('readonly', False)], 'feeding': [('readonly', False)]})
    lot = fields.Char(u'批号')
    goods_qty = fields.Float(u'组合件数量', default=1, digits=dp.get_precision('Quantity'),
                             readonly=True,
                             states={'draft': [('readonly', False)], 'feeding': [
                                 ('readonly', False)]},
                             help=u"(选择使用物料清单后)当更改这个数量的时候后自动的改变相应的子件的数量")
    voucher_id = fields.Many2one(
        'voucher', copy=False, ondelete='restrict', string=u'入库凭证号')
    out_voucher_id = fields.Many2one(
        'voucher', copy=False, ondelete='restrict', string=u'出库凭证号')

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
        if self.goods_id and not self.bom_id:
            self.line_in_ids = [{'goods_id': self.goods_id.id, 'product_uos_qty': 1, 'goods_qty': 1,
                                 'uom_id': self.goods_id.uom_id.id, 'uos_id': self.goods_id.uos_id.id,
                                 'type': 'in'}]

    @api.onchange('goods_qty')
    def onchange_goods_qty(self):
        """
        改变商品数量时(wh_assembly 中的goods_qty) 根据物料清单的 数量的比例及成本价的计算
        算出新的组合件或者子件的 数量 (line.goods_qty / parent_line_goods_qty * self.goods_qty
        line.goods_qty 子件商品数量
        parent_line_goods_qty 物料清单组合件商品数量
        self.goods_qty 所要的组合件的商品数量
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
                            'attribute_id': line.attribute_id.id,
                            'warehouse_id': self.env['warehouse'].get_warehouse_by_type(
                                'production').id,
                            'warehouse_dest_id': warehouse_id.id,
                            'uom_id': line.goods_id.uom_id.id,
                            'goods_qty': self.goods_qty,
                            'goods_uos_qty': self.goods_qty / line.goods_id.conversion,
                            'uos_id': line.goods_id.uos_id.id,
                            'type': 'in',
                            } for line in self.bom_id.line_parent_ids]
            parent_line_goods_qty = self.bom_id.line_parent_ids[0].goods_qty
            for line in self.bom_id.line_child_ids:
                cost, cost_unit = line.goods_id. \
                    get_suggested_cost_by_warehouse(
                        warehouse_id[0], line.goods_qty / parent_line_goods_qty * self.goods_qty)
                local_goods_qty = line.goods_qty / parent_line_goods_qty * self.goods_qty
                line_out_ids.append({
                    'goods_id': line.goods_id.id,
                    'attribute_id': line.attribute_id.id,
                    'warehouse_id': warehouse_id.id,
                    'warehouse_dest_id': self.env[
                        'warehouse'].get_warehouse_by_type('production'),
                    'uom_id': line.goods_id.uom_id.id,
                    'goods_qty':  local_goods_qty,
                    'cost_unit': cost_unit,
                    'cost': cost,
                    'goods_uos_qty': local_goods_qty / line.goods_id.conversion,
                    'uos_id': line.goods_id.uos_id.id,
                    'type': 'out',
                })
            self.line_in_ids = False
            self.line_out_ids = False
            if line_in_ids:
                self.line_in_ids = line_in_ids
            if line_out_ids:
                self.line_out_ids = line_out_ids
        elif self.line_in_ids:
            self.line_in_ids[0].goods_qty = self.goods_qty

    @api.one
    def check_parent_length(self):
        if not len(self.line_in_ids) or not len(self.line_out_ids):
            raise UserError(u'组合件和子件的商品必须存在')

    def create_voucher_line(self, data):
        return [self.env['voucher.line'].create(data_line) for data_line in data]

    def create_vourcher_line_data(self, assembly, voucher_row):
        """
        准备入库凭证行数据
        借：库存商品（商品上）
        贷：生产成本-基本生产成本（核算分类上）
        :param assembly: 组装单
        :param voucher_row: 入库凭证
        :return:
        """
        line_out_data, line_in_data = [], []
        line_out_credit = 0.0
        for line_out in assembly.line_out_ids:
            if line_out.cost:
                line_out_credit += line_out.cost

        if line_out_credit:  # 贷方行
            account_id = self.finance_category_id.account_id.id
            line_out_data.append({'credit': line_out_credit,
                                  'goods_id': False,
                                  'voucher_id': voucher_row.id,
                                  'account_id': account_id,
                                  'name': u'%s 原料 %s' % (assembly.move_id.name, assembly.move_id.note or '')
                                  })
        for line_in in assembly.line_in_ids:  # 借方行
            if line_in.cost:
                account_id = line_in.goods_id.category_id.account_id.id
                line_in_data.append({'debit': line_in.cost,
                                     'goods_id': line_in.goods_id.id,
                                     'goods_qty': line_in.goods_qty,
                                     'voucher_id': voucher_row.id,
                                     'account_id': account_id,
                                     'name': u'%s 成品 %s' % (assembly.move_id.name, assembly.move_id.note or '')})
        return line_out_data + line_in_data

    def wh_assembly_create_voucher_line(self, assembly, voucher_row):
        """
        创建入库凭证行
        :param assembly: 组装单
        :param voucher_row: 入库凭证
        :return:
        """
        voucher_line_data = []
        # 贷方行
        if assembly.fee:
            account_row = assembly.create_uid.company_id.operating_cost_account_id
            voucher_line_data.append({'name': u'组装费用', 'account_id': account_row.id,
                                      'credit': assembly.fee, 'voucher_id': voucher_row.id})
        voucher_line_data += self.create_vourcher_line_data(
            assembly, voucher_row)

        self.create_voucher_line(voucher_line_data)

    def pre_out_vourcher_line_data(self, assembly, voucher):
        """
        准备出库凭证行数据
        借：生产成本-基本生产成本（核算分类上）
        贷：库存商品（商品上）
        :param assembly: 组装单
        :param voucher: 出库凭证
        :return: 出库凭证行数据
        """
        line_out_data, line_in_data = [], []
        line_out_debit = 0.0
        for line_out in assembly.line_out_ids:
            if line_out.cost:
                line_out_debit += line_out.cost

        if line_out_debit:  # 借方行
            account_id = self.finance_category_id.account_id.id
            line_in_data.append({'debit': line_out_debit,
                                 'goods_id': False,
                                 'voucher_id': voucher.id,
                                 'account_id': account_id,
                                 'name': u'%s 成品 %s' % (assembly.move_id.name, assembly.move_id.note or '')
                                 })
        for line_out in assembly.line_out_ids:  # 贷方行
            if line_out.cost:
                account_id = line_out.goods_id.category_id.account_id.id
                line_out_data.append({'credit': line_out.cost,
                                      'goods_id': line_out.goods_id.id,
                                      'goods_qty': line_out.goods_qty,
                                      'voucher_id': voucher.id,
                                      'account_id': account_id,
                                      'name': u'%s 原料 %s' % (assembly.move_id.name, assembly.move_id.note or '')})
        return line_out_data + line_in_data

    def create_out_voucher_line(self, assembly, voucher):
        """
        创建出库凭证行
        :param assembly: 组装单
        :param voucher: 出库凭证
        :return:
        """
        voucher_line_data = self.pre_out_vourcher_line_data(assembly, voucher)

        self.create_voucher_line(voucher_line_data)

    def wh_assembly_create_voucher(self):
        """
        生成入库凭证并审核
        :return:
        """
        for assembly in self:
            voucher_row = self.env['voucher'].create({'date': assembly.date, 'ref': '%s,%s' % (self._name, self.id)})
            self.wh_assembly_create_voucher_line(assembly, voucher_row)  # 入库凭证
            assembly.voucher_id = voucher_row.id
            voucher_row.voucher_done()

    def create_out_voucher(self):
        """
        生成出库凭证并审核
        :return:
        """
        for assembly in self:
            out_voucher = self.env['voucher'].create({'date': assembly.date, 'ref': '%s,%s' % (self._name, self.id)})
            self.create_out_voucher_line(assembly, out_voucher)  # 出库凭证
            assembly.out_voucher_id = out_voucher.id
            out_voucher.voucher_done()

    @api.multi
    def check_is_child_enable(self):
        for child_line in self.line_out_ids:
            for parent_line in self.line_in_ids:
                if child_line.goods_id.id == parent_line.goods_id.id and child_line.attribute_id.id == parent_line.attribute_id.id:
                    raise UserError(u'子件中不能包含与组合件中相同的 产品+属性，%s' % parent_line.goods_id.name)

    @api.multi
    def approve_feeding(self):
        ''' 发料 '''
        for order in self:
            if order.state == 'feeding':
                raise UserError(u'请不要重复发料')
            order.check_parent_length()
            order.check_is_child_enable()

            for line_out in order.line_out_ids:
                if line_out.state != 'done':
                    line_out.action_done()

            order.create_out_voucher()  # 生成出库凭证并审核
            order.state = 'feeding'
            return

    @api.multi
    def approve_order(self):
        ''' 成品入库 '''
        for order in self:
            if order.state == 'done':
                raise UserError(u'请不要重复执行成品入库')
            if order.state != 'feeding':
                raise UserError(u'请先投料')
            order.move_id.check_qc_result()  # 检验质检报告是否上传
            if order.lot:                     # 入库批次
                for line in order.line_in_ids:
                    line.lot = order.lot
            order.line_in_ids.action_done()  # 完成成品入库

            wh_internal = self.env['wh.internal'].search([('ref', '=', order.move_id.name)])
            if wh_internal:
                wh_internal.approve_order()

            order.update_parent_cost()
            order.wh_assembly_create_voucher()  # 生成入库凭证并审核

            order.approve_uid = self.env.uid
            order.approve_date = fields.Datetime.now(self)
            order.state = 'done'
            order.move_id.state = 'done'
            return

    @api.multi
    def cancel_approved_order(self):
        for order in self:
            if order.state == 'feeding':
                raise UserError(u'请不要重复撤销')
            # 反审核入库到废品仓的移库单
            wh_internal = self.env['wh.internal'].search([('ref', '=', order.move_id.name)])
            if wh_internal:
                wh_internal.cancel_approved_order()
                wh_internal.unlink()
            order.line_in_ids.action_draft()

            # 删除入库凭证
            voucher, order.voucher_id = order.voucher_id, False
            if voucher.state == 'done':
                voucher.voucher_draft()
            voucher.unlink()

            order.approve_uid = False
            order.approve_date = False
            order.state = 'feeding'
            order.move_id.state = 'draft'

    @api.multi
    @ inherits()
    def unlink(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(u'只能删除草稿状态的单据')

        return order.move_id.unlink()

    @api.model
    @create_name
    @create_origin
    def create(self, vals):
        vals.update({'finance_category_id': self.env.ref(
            'finance.categ_ass_disass').id})
        self = super(WhAssembly, self).create(vals)
        self.update_parent_cost()
        return self

    @api.multi
    def write(self, vals):
        res = super(WhAssembly, self).write(vals)
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
                'type': 'in',
                'goods_id': line.goods_id.id,
                'warehouse_id': self.env['warehouse'].get_warehouse_by_type(
                    'production').id,
                'warehouse_dest_id': warehouse_id.id,
                'uom_id': line.goods_id.uom_id.id,
                'goods_qty': line.goods_qty,
                'goods_uos_qty': line.goods_qty / line.goods_id.conversion,
                'uos_id': line.goods_id.uos_id.id,
                'attribute_id': line.attribute_id.id,
            } for line in self.bom_id.line_parent_ids]

            for line in self.bom_id.line_child_ids:
                cost, cost_unit = line.goods_id. \
                    get_suggested_cost_by_warehouse(
                        warehouse_id[0], line.goods_qty)
                line_out_ids.append({
                    'type': 'out',
                    'goods_id': line.goods_id.id,
                    'warehouse_id': warehouse_id.id,
                    'warehouse_dest_id': self.env[
                            'warehouse'].get_warehouse_by_type('production').id,
                    'uom_id': line.goods_id.uom_id.id,
                    'goods_qty': line.goods_qty,
                    'cost_unit': cost_unit,
                    'cost': cost,
                    'goods_uos_qty': line.goods_qty / line.goods_id.conversion,
                    'uos_id': line.goods_id.uos_id.id,
                    'attribute_id': line.attribute_id.id,
                })
            self.line_in_ids = False
            self.line_out_ids = False
        else:
            self.goods_qty = 1

        if len(line_in_ids) == 1:
            """当物料清单中只有一个组合件的时候,默认本单据只有一个组合件 设置is_many_to_many_combinations 为False
                使试图只能在 many2one中选择一个商品(并且只能选择在物料清单中的商品),并且回写数量"""
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


class outsource(models.Model):
    _name = 'outsource'
    _description = u'委外加工单'
    _inherit = ['mail.thread']
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    state = fields.Selection([('draft', u'草稿'),
                              ('feeding', u'已发料'),
                              ('done', u'完成'),
                              ('cancel', u'已作废')],
                             u'状态', copy=False, default='draft',
                             index=True,
                             help=u'委外加工单状态标识，新建时状态为草稿；发料后状态为已发料，可以多次投料；成品入库后状态为完成。')
    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade',
                              help=u'委外加工单对应的移库单')
    bom_id = fields.Many2one('wh.bom', u'物料清单', domain=[('type', '=', 'outsource')],
                             context={'type': 'outsource'}, ondelete='restrict',
                             readonly=True,
                             states={'draft': [('readonly', False)], 'feeding': [
                                 ('readonly', False)]},
                             help=u'委外加工单对应的物料清单')
    is_many_to_many_combinations = fields.Boolean(u'专家模式', default=False, help=u"通用情况是一对多的组合,当为False时\
                            视图只能选则一个商品作为组合件,(选择物料清单后)此时选择数量会更改子件的数量,当为True时则可选择多个组合件,此时组合件商品数量\
                            不会自动影响子件的数量")
    goods_id = fields.Many2one('goods', string=u'组合件商品',
                               readonly=True,
                               states={'draft': [('readonly', False)], 'feeding': [('readonly', False)]})
    lot = fields.Char(u'批号')
    goods_qty = fields.Float(u'组合件数量', default=1, digits=dp.get_precision('Quantity'),
                             readonly=True,
                             states={'draft': [('readonly', False)], 'feeding': [
                                 ('readonly', False)]},
                             help=u"(选择使用物料清单后)当更改这个数量的时候后自动的改变相应的子件的数量")
    voucher_id = fields.Many2one(
        'voucher', copy=False, ondelete='restrict', string=u'入库凭证号')
    out_voucher_id = fields.Many2one(
        'voucher', copy=False, ondelete='restrict', string=u'出库凭证号')

    outsource_partner_id = fields.Many2one('partner', string=u'委外供应商',
                                           readonly=True,
                                           states={'draft': [('readonly', False)], 'feeding': [
                                               ('readonly', False)]},
                                           required=True)
    wh_assembly_id = fields.Many2one('wh.assembly', string=u'关联的组装单',
                                     readonly=True,
                                     states={'draft': [('readonly', False)], 'feeding': [('readonly', False)]})
    outsource_fee = fields.Float(string=u'委外费用',
                                 digits=dp.get_precision('Amount'),
                                 readonly=True,
                                 states={'draft': [('readonly', False)], 'feeding': [('readonly', False)]})
    invoice_id = fields.Many2one('money.invoice',
                                 copy=False,
                                 ondelete='set null',
                                 string=u'发票号')

    @api.onchange('goods_id')
    def onchange_goods_id(self):
        if self.goods_id and not self.bom_id:
            self.line_in_ids = False
            self.line_in_ids = [{'goods_id': self.goods_id.id, 'product_uos_qty': 1, 'goods_qty': 1,
                                 'uom_id': self.goods_id.uom_id.id, 'uos_id': self.goods_id.uos_id.id,
                                 'type': 'in'}]

    @api.onchange('goods_qty')
    def onchange_goods_qty(self):
        """
        改变商品数量时(outsource 中的goods_qty) 根据 物料清单 中的数量的比例
        计算出新的组合件或子件的数量
    (line.goods_qty / parent_line_goods_qty * self.goods_qty
        line.goods_qty 子件商品数量
        parent_line_goods_qty 物料清单组合件商品数量
        self.goods_qty 所要的组合件的商品数量
        line.goods_qty /parent_line_goods_qty 得出子件和组合件的比例
        line.goods_qty / parent_line_goods_qty * self.goods_qty 得出子件实际的数量的数量
        )
        :return:line_out_ids ,line_in_ids
        """
        line_out_ids, line_in_ids = [], []
        warehouse_id = self.env['warehouse'].search(
            [('type', '=', 'stock')], limit=1)
        if self.bom_id:  # 存在 物料清单
            line_in_ids = [{'goods_id': line.goods_id.id,
                            'attribute_id': line.attribute_id.id,
                            'warehouse_id': self.env['warehouse'].get_warehouse_by_type('production').id,
                            'warehouse_dest_id': warehouse_id.id,
                            'uom_id': line.goods_id.uom_id.id,
                            'goods_qty': self.goods_qty,
                            'goods_uos_qty': self.goods_qty / line.goods_id.conversion,
                            'uos_id': line.goods_id.uos_id.id,
                            'type': 'in'
                            } for line in self.bom_id.line_parent_ids]

            parent_line_goods_qty = self.bom_id.line_parent_ids[0].goods_qty

            for line in self.bom_id.line_child_ids:
                cost, cost_unit = line.goods_id.get_suggested_cost_by_warehouse(
                    warehouse_id[0], line.goods_qty / parent_line_goods_qty * self.goods_qty)

                local_goods_qty = line.goods_qty / parent_line_goods_qty * self.goods_qty

                line_out_ids.append({
                    'goods_id': line.goods_id.id,
                    'attribute_id': line.attribute_id.id,
                    'warehouse_id': warehouse_id.id,
                    'warehouse_dest_id': self.env['warehouse'].get_warehouse_by_type('production'),
                    'uom_id': line.goods_id.uom_id.id,
                    'goods_qty': local_goods_qty,
                    'cost_unit': cost_unit,
                    'cost': cost,
                    'goods_uos_qty': local_goods_qty / line.goods_id.conversion,
                    'uos_id': line.goods_id.uos_id.id,
                    'type': 'out',
                })

            self.line_in_ids = False
            self.line_out_ids = False
            self.line_out_ids = line_out_ids
            self.line_in_ids = line_in_ids
        elif self.line_in_ids:  # 不存在 物料清单，有组合单行
            self.line_in_ids[0].goods_qty = self.goods_qty

    @api.onchange('bom_id')
    def onchange_bom(self):
        line_out_ids, line_in_ids = [], []
        domain = {}
        warehouse_id = self.env['warehouse'].search(
            [('type', '=', 'stock')], limit=1)
        if self.bom_id:
            line_in_ids = [{
                'goods_id': line.goods_id.id,
                'attribute_id': line.attribute_id.id,
                'warehouse_id': self.env['warehouse'].get_warehouse_by_type('production').id,
                'warehouse_dest_id': warehouse_id.id,
                'uom_id': line.goods_id.uom_id.id,
                'goods_qty': line.goods_qty,
                'goods_uos_qty': line.goods_qty / line.goods_id.conversion,
                'uos_id': line.goods_id.uos_id.id,
                'type': 'in',
            } for line in self.bom_id.line_parent_ids]

            for line in self.bom_id.line_child_ids:
                cost, cost_unit = line.goods_id. \
                    get_suggested_cost_by_warehouse(
                        warehouse_id[0], line.goods_qty)
                line_out_ids.append({
                    'goods_id': line.goods_id.id,
                    'attribute_id': line.attribute_id.id,
                    'warehouse_id': warehouse_id.id,
                    'warehouse_dest_id': self.env[
                        'warehouse'].get_warehouse_by_type('production').id,
                    'uom_id': line.goods_id.uom_id.id,
                    'goods_qty': line.goods_qty,
                    'cost_unit': cost_unit,
                    'cost': cost,
                    'goods_uos_qty': line.goods_qty / line.goods_id.conversion,
                    'uos_id': line.goods_id.uos_id.id,
                    'type': 'out',
                })
            self.line_in_ids = False
            self.line_out_ids = False
        else:
            self.goods_qty = 1

        if len(line_in_ids) == 1:
            """当物料清单中只有一个组合件的时候,默认本单据只有一个组合件 设置is_many_to_many_combinations 为False
                使视图只能在 many2one中选择一个商品(并且只能选择在物料清单中的商品),并且回写数量"""
            self.is_many_to_many_combinations = False
            self.goods_qty = line_in_ids[0].get("goods_qty")
            self.goods_id = line_in_ids[0].get("goods_id")
            domain = {'goods_id': [('id', '=', self.goods_id.id)]}
        elif len(line_in_ids) > 1:
            self.is_many_to_many_combinations = True

        if line_out_ids:
            self.line_out_ids = line_out_ids
        if line_in_ids:
            self.line_in_ids = line_in_ids

        return {'domain': domain}

    def apportion_cost(self, cost):
        for outsource in self:
            if not outsource.line_in_ids:
                continue

            collects = []
            ignore_move = [line.id for line in outsource.line_in_ids]
            for parent in outsource.line_in_ids:
                collects.append((parent,
                                 parent.goods_id.get_suggested_cost_by_warehouse(
                                     parent.warehouse_dest_id, parent.goods_qty,
                                     lot_id=parent.lot_id,
                                     attribute=parent.attribute_id,
                                     ignore_move=ignore_move)[0]
                                 ))

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
        for outsource in self:
            cost = sum(child.cost for child in outsource.line_out_ids) + \
                outsource.outsource_fee
            outsource.apportion_cost(cost)
        return True

    @api.multi
    @inherits()
    def unlink(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(u'只删除草稿状态的单据')

        return order.move_id.unlink()

    @api.model
    @create_name
    @create_origin
    def create(self, vals):
        vals.update({'finance_category_id': self.env.ref(
            'finance.categ_outsource').id})
        self = super(outsource, self).create(vals)
        self.update_parent_cost()
        return self

    @api.multi
    def write(self, vals):
        res = super(outsource, self).write(vals)
        self.update_parent_cost()
        return res

    @api.multi
    def check_parent_length(self):
        for outsource_line in self:
            if not len(outsource_line.line_in_ids) or not len(outsource_line.line_out_ids):
                raise UserError(u'委外加工单必须存在组合件和子件明细行。')

    def _create_money_invoice(self):
        categ = self.env.ref('money.core_category_purchase')
        source_id = self.env['money.invoice'].create({
            'name': self.name,
            'partner_id': self.outsource_partner_id.id,
            'category_id': categ.id,
            'date': fields.Date.context_today(self),
            'amount': self.outsource_fee,
            'reconciled': 0,
            'to_reconcile': self.outsource_fee,
            'date_due': fields.Date.context_today(self),
            'note': self.note or '',
        })
        if source_id:
            self.invoice_id = source_id.id
        return source_id

    def create_voucher_line(self, data):
        return [self.env['voucher.line'].create(data_line) for data_line in data]

    def create_vourcher_line_data(self, outsource, voucher_row):
        """
        准备入库凭证行数据
        借：库存商品（商品上）
        贷：生产成本-基本生产成本（核算分类上）
        :param outsource: 委外加工单
        :param voucher_row: 入库凭证
        :return:
        """
        line_out_data, line_in_data = [], []
        line_out_credit = 0.0
        for line_out in outsource.line_out_ids:
            if line_out.cost:
                line_out_credit += line_out.cost

        if line_out_credit:  # 贷方行
            account_id = self.finance_category_id.account_id.id
            line_out_data.append({'credit': line_out_credit,
                                  'goods_id': False,
                                  'voucher_id': voucher_row.id,
                                  'account_id': account_id,
                                  'name': u'%s 原料 %s' % (outsource.move_id.name, outsource.move_id.note or '')
                                  })
        for line_in in outsource.line_in_ids:  # 借方行
            if line_in.cost:
                account_id = line_in.goods_id.category_id.account_id.id
                line_in_data.append({'debit': line_in.cost,
                                     'goods_id': line_in.goods_id.id,
                                     'goods_qty': line_in.goods_qty,
                                     'voucher_id': voucher_row.id,
                                     'account_id': account_id,
                                     'name': u'%s 成品 %s' % (outsource.move_id.name, outsource.move_id.note or '')
                                     })
        return line_out_data + line_in_data

    def pre_out_vourcher_line_data(self, outsource, voucher):
        """
        准备出库凭证行数据
        借：委托加工物资（核算分类上）
        贷：库存商品（商品上）
        :param outsource: 委外加工单
        :param voucher: 出库凭证
        :return: 出库凭证行数据
        """
        line_out_data, line_in_data = [], []
        line_out_debit = 0.0
        for line_out in outsource.line_out_ids:
            if line_out.cost:
                line_out_debit += line_out.cost

        if line_out_debit:  # 借方行
            account_id = self.finance_category_id.account_id.id
            line_in_data.append({'debit': line_out_debit,
                                 'goods_id': False,
                                 'voucher_id': voucher.id,
                                 'account_id': account_id,
                                 'name': u'%s 成品 %s' % (outsource.move_id.name, outsource.move_id.note or '')
                                 })
        for line_out in outsource.line_out_ids:  # 贷方行
            if line_out.cost:
                account_id = line_out.goods_id.category_id.account_id.id
                line_out_data.append({'credit': line_out.cost,
                                      'goods_id': line_out.goods_id.id,
                                      'goods_qty': line_out.goods_qty,
                                      'voucher_id': voucher.id,
                                      'account_id': account_id,
                                      'name': u'%s 原料 %s' % (outsource.move_id.name, outsource.move_id.note or '')})
        return line_out_data + line_in_data

    def outsource_create_voucher_line(self, outsource, voucher_row):
        """
        创建入库凭证行
        :param outsource: 委外加工单
        :param voucher_row: 入库凭证
        :return:
        """
        voucher_line_data = []
        if outsource.outsource_fee:
            # 贷方行
            voucher_line_data.append({'name': u'委外费用',
                                      'account_id': self.env.ref('money.core_category_purchase').account_id.id, # 采购发票类别对应的科目
                                      'credit': outsource.outsource_fee, 'voucher_id': voucher_row.id})

        voucher_line_data += self.create_vourcher_line_data(
            outsource, voucher_row)
        self.create_voucher_line(voucher_line_data)

    def create_out_voucher_line(self, outsource, voucher):
        """
        创建出库凭证行
        :param outsource: 委外加工单
        :param voucher: 出库凭证
        :return:
        """
        voucher_line_data = self.pre_out_vourcher_line_data(outsource, voucher)

        self.create_voucher_line(voucher_line_data)

    def outsource_create_voucher(self):
        """
        生成入库凭证并审核
        :return:
        """
        for outsource in self:
            voucher_row = self.env['voucher'].create({'date': outsource.date, 'ref': '%s,%s' % (self._name, self.id)})
            self.outsource_create_voucher_line(outsource, voucher_row)  # 入库凭证

            outsource.voucher_id = voucher_row.id
            voucher_row.voucher_done()

    def create_out_voucher(self):
        """
        生成出库凭证并审核
        :return:
        """
        for outsource in self:
            out_voucher = self.env['voucher'].create({'date': outsource.date, 'ref': '%s,%s' % (self._name, self.id)})
            self.create_out_voucher_line(outsource, out_voucher)  # 出库凭证

            outsource.out_voucher_id = out_voucher.id
            out_voucher.voucher_done()

    @api.multi
    def check_is_child_enable(self):
        for child_line in self.line_out_ids:
            for parent_line in self.line_in_ids:
                if child_line.goods_id.id == parent_line.goods_id.id and child_line.attribute_id.id == parent_line.attribute_id.id:
                    raise UserError(u'子件中不能包含与组合件中相同的 产品+属性，%s' % parent_line.goods_id.name)

    @api.multi
    def approve_feeding(self):
        ''' 发料 '''
        for order in self:
            if order.state == 'feeding':
                raise UserError(u'请不要重复发料')
            order.check_parent_length()
            order.check_is_child_enable()

            for line_out in order.line_out_ids:
                if line_out.state != 'done':
                    line_out.action_done()

            order.create_out_voucher()  # 生成出库凭证并审核
            order.state = 'feeding'
            return

    @api.multi
    def approve_order(self):
        ''' 成品入库 '''
        for order in self:
            if order.state == 'done':
                raise UserError(u'请不要重复执行成品入库')
            if order.state != 'feeding':
                raise UserError(u'请先投料')
            order.move_id.check_qc_result()  # 检验质检报告是否上传
            if order.lot:                     # 入库批次
                for line in order.line_in_ids:
                    line.lot = order.lot
            order.line_in_ids.action_done()  # 完成成品入库

            wh_internal = self.env['wh.internal'].search([('ref', '=', order.move_id.name)])
            if wh_internal:
                wh_internal.approve_order()

            # 如果委外费用存在，生成 结算单
            if order.outsource_fee:
                order._create_money_invoice()

            order.update_parent_cost()
            order.outsource_create_voucher()  # 生成入库凭证并审核

            order.approve_uid = self.env.uid
            order.approve_date = fields.Datetime.now(self)
            order.state = 'done'
            order.move_id.state = 'done'
            return

    @api.multi
    def cancel_approved_order(self):
        for order in self:
            if order.state == 'feeding':
                raise UserError(u'请不要重复撤销')
            # 反审核入库到废品仓的移库单
            wh_internal = self.env['wh.internal'].search([('ref', '=', order.move_id.name)])
            if wh_internal:
                wh_internal.cancel_approved_order()
                wh_internal.unlink()
            order.line_in_ids.action_draft()

            # 删除入库凭证
            voucher, order.voucher_id = order.voucher_id, False
            if voucher.state == 'done':
                voucher.voucher_draft()
            voucher.unlink()

            if order.invoice_id:
                order.invoice_id.money_invoice_draft()
                order.invoice_id.unlink()

            order.approve_uid = False
            order.approve_date = False
            order.state = 'feeding'
            order.move_id.state = 'draft'


class WhDisassembly(models.Model):
    _name = 'wh.disassembly'
    _description = u'拆卸单'
    _inherit = ['mail.thread']
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    state = fields.Selection([('draft', u'草稿'),
                              ('feeding', u'已发料'),
                              ('done', u'完成'),
                              ('cancel', u'已作废')],
                             u'状态', copy=False, default='draft',
                             index=True,
                             help=u'拆卸单状态标识，新建时状态为草稿；发料后状态为已发料，可以多次投料；成品入库后状态为完成。')
    move_id = fields.Many2one(
        'wh.move', u'移库单', required=True, index=True, ondelete='cascade',
        help=u'拆卸单对应的移库单')
    bom_id = fields.Many2one(
        'wh.bom', u'物料清单', domain=[('type', '=', 'disassembly')],
        context={'type': 'disassembly'}, ondelete='restrict',
        readonly=True,
        states={'draft': [('readonly', False)], 'feeding': [
            ('readonly', False)]},
        help=u'拆卸单对应的物料清单')
    fee = fields.Float(
        u'拆卸费用', digits=dp.get_precision('Amount'),
        readonly=True,
        states={'draft': [('readonly', False)], 'feeding': [
            ('readonly', False)]},
        help=u'拆卸单对应的拆卸费用, 拆卸费用+拆卸行出库成本作为子件的入库成本')
    is_many_to_many_combinations = fields.Boolean(u'专家模式', default=False, help=u"通用情况是一对多的组合,当为False时\
                            视图只能选则一个商品作为组合件,(选择物料清单后)此时选择数量会更改子件的数量,当为True时则可选择多个组合件,此时组合件商品数量\
                            不会自动影响子件的数量")
    goods_id = fields.Many2one('goods', string=u'组合件商品',
                               readonly=True,
                               states={'draft': [('readonly', False)], 'feeding': [('readonly', False)]},)
    lot_id = fields.Many2one('wh.move.line', u'批号',
                             help=u'用于拆卸的组合件批号')
    goods_qty = fields.Float(u'组合件数量', default=1, digits=dp.get_precision('Quantity'),
                             readonly=True,
                             states={'draft': [('readonly', False)], 'feeding': [
                                 ('readonly', False)]},
                             help=u"(选择使用物料清单后)当更改这个数量的时候后自动的改变相应的子件的数量")
    voucher_id = fields.Many2one(
        'voucher', copy=False, ondelete='restrict', string=u'入库凭证号')
    out_voucher_id = fields.Many2one(
        'voucher', copy=False, ondelete='restrict', string=u'出库凭证号')

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
            raise UserError(u'组合件和子件的商品必须存在')

    def create_voucher_line(self, data):
        return [self.env['voucher.line'].create(data_line) for data_line in data]

    def create_vourcher_line_data(self, disassembly, voucher_row):
        """
        准备入库凭证行数据
        借：库存商品（商品上）
        贷：生产成本-基本生产成本（核算分类上）
        :param disassembly: 拆卸单
        :param voucher_row: 入库库凭证
        :return:
        """
        line_out_data, line_in_data = [], []
        line_in_credit = 0.0
        for line_in in disassembly.line_in_ids:
            if line_in.cost:
                line_in_credit += line_in.cost

        if line_in_credit:  # 贷方行
            account_id = self.finance_category_id.account_id.id
            line_out_data.append({'credit': line_in_credit,
                                  'goods_id': False,
                                  'voucher_id': voucher_row.id,
                                  'account_id': account_id,
                                  'name': u'%s 原料 %s' % (disassembly.move_id.name, disassembly.move_id.note or '')
                                  })
        for line_in in disassembly.line_in_ids:  # 借方行
            if line_in.cost:
                account_id = line_in.goods_id.category_id.account_id.id
                line_in_data.append({'debit': line_in.cost,
                                     'goods_id': line_in.goods_id.id,
                                     'goods_qty': line_in.goods_qty,
                                     'voucher_id': voucher_row.id,
                                     'account_id': account_id,
                                     'name': u'%s 成品 %s' % (disassembly.move_id.name, disassembly.move_id.note or '')
                                     })
        return line_out_data + line_in_data

    def pre_out_vourcher_line_data(self, disassembly, voucher):
        """
        准备出库凭证行数据
        借：生产成本-基本生产成本（核算分类上）
        贷：库存商品（商品上）
        :param disassembly: 拆卸单
        :param voucher: 出库凭证
        :return: 出库凭证行数据
        """
        line_out_data, line_in_data = [], []
        line_out_debit = 0.0
        for line_out in disassembly.line_out_ids:
            line_out_debit += line_out.cost

        if line_out_debit:  # 借方行
            account_id = self.finance_category_id.account_id.id
            line_in_data.append({'debit': line_out_debit,
                                 'goods_id': False,
                                 'voucher_id': voucher.id,
                                 'account_id': account_id,
                                 'name': u'%s 成品 %s' % (disassembly.move_id.name, disassembly.move_id.note or '')
                                 })
        for line_out in disassembly.line_out_ids:  # 贷方行
            if line_out.cost:
                account_id = line_out.goods_id.category_id.account_id.id
                line_out_data.append({'credit': line_out.cost + disassembly.fee,
                                      'goods_id': line_out.goods_id.id,
                                      'goods_qty': line_out.goods_qty,
                                      'voucher_id': voucher.id,
                                      'account_id': account_id,
                                      'name': u'%s 原料 %s' % (disassembly.move_id.name, disassembly.move_id.note or '')})
        return line_out_data + line_in_data

    def wh_disassembly_create_voucher_line(self, disassembly, voucher_row):
        """
        创建入库凭证行
        :param disassembly:
        :param voucher_row:
        :return:
        """
        voucher_line_data = []
        voucher_line_data += self.create_vourcher_line_data(
            disassembly, voucher_row)
        self.create_voucher_line(voucher_line_data)

    def create_out_voucher_line(self, disassembly, voucher):
        """
        创建出库凭证行
        :param disassembly: 拆卸单
        :param voucher: 出库凭证
        :return:
        """
        voucher_line_data = []
        # 借方行
        if disassembly.fee:
            account = disassembly.create_uid.company_id.operating_cost_account_id
            voucher_line_data.append({'name': u'拆卸费用', 'account_id': account.id,
                                      'debit': disassembly.fee, 'voucher_id': voucher.id})
        voucher_line_data += self.pre_out_vourcher_line_data(
            disassembly, voucher)

        self.create_voucher_line(voucher_line_data)

    def wh_disassembly_create_voucher(self):
        """
        生成入库凭证并审核
        :return:
        """
        for disassembly in self:
            voucher_row = self.env['voucher'].create(
                {'date': disassembly.date, 'ref': '%s,%s' % (self._name, self.id)})
            self.wh_disassembly_create_voucher_line(
                disassembly, voucher_row)   # 入库凭证
            disassembly.voucher_id = voucher_row.id
            voucher_row.voucher_done()

    def create_out_voucher(self):
        """
        生成出库凭证并审核
        :return:
        """
        for disassembly in self:
            out_voucher = self.env['voucher'].create(
                {'date': disassembly.date, 'ref': '%s,%s' % (self._name, self.id)})
            self.create_out_voucher_line(disassembly, out_voucher)  # 出库凭证
            disassembly.out_voucher_id = out_voucher.id
            out_voucher.voucher_done()

    @api.multi
    def check_is_child_enable(self):
        for child_line in self.line_in_ids:
            for parent_line in self.line_out_ids:
                if child_line.goods_id.id == parent_line.goods_id.id and child_line.attribute_id.id == parent_line.attribute_id.id:
                    raise UserError(u'子件中不能包含与组合件中相同的 产品+属性，%s' % parent_line.goods_id.name)

    def approve_feeding(self):
        ''' 发料 '''
        for order in self:
            if order.state == 'feeding':
                raise UserError(u'请不要重复发料')
            order.check_parent_length()
            order.check_is_child_enable()

            for line_out in order.line_out_ids:
                if line_out.state != 'done':
                    if order.lot_id:      #出库批次
                        line_out.lot_id = order.lot_id
                    line_out.action_done()

            order.create_out_voucher()   # 生成出库凭证并审核
            order.state = 'feeding'
            return

    @api.multi
    def approve_order(self):
        ''' 成品入库 '''
        for order in self:
            if order.state == 'done':
                raise UserError(u'请不要重复执行成品入库')
            if order.state != 'feeding':
                raise UserError(u'请先投料')
            order.move_id.check_qc_result()  # 检验质检报告是否上传
            order.line_in_ids.action_done()  # 完成成品入库

            wh_internal = self.env['wh.internal'].search([('ref', '=', order.move_id.name)])
            if wh_internal:
                wh_internal.approve_order()

            order.update_child_cost()
            order.wh_disassembly_create_voucher()  # 生成入库凭证并审核

            order.approve_uid = self.env.uid
            order.approve_date = fields.Datetime.now(self)
            order.state = 'done'
            order.move_id.state = 'done'
            return

    @api.multi
    def cancel_approved_order(self):
        for order in self:
            if order.state == 'feeding':
                raise UserError(u'请不要重复撤销')
            # 反审核入库到废品仓的移库单
            wh_internal = self.env['wh.internal'].search([('ref', '=', order.move_id.name)])
            if wh_internal:
                wh_internal.cancel_approved_order()
                wh_internal.unlink()
            order.line_in_ids.action_draft()
            # 删除入库凭证
            voucher, order.voucher_id = order.voucher_id, False
            if voucher.state == 'done':
                voucher.voucher_draft()
            voucher.unlink()

            order.approve_uid = False
            order.approve_date = False
            order.state = 'feeding'
            order.move_id.state = 'draft'

    @api.multi
    @inherits()
    def unlink(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(u'只删除草稿状态的单据')

        return order.move_id.unlink()

    @api.model
    @create_name
    @create_origin
    def create(self, vals):
        vals.update({'finance_category_id': self.env.ref(
            'finance.categ_ass_disass').id})
        self = super(WhDisassembly, self).create(vals)
        self.update_child_cost()
        return self

    @api.multi
    def write(self, vals):
        res = super(WhDisassembly, self).write(vals)
        self.update_child_cost()
        return res

    @api.onchange('goods_id')
    def onchange_goods_id(self):
        if self.goods_id and not self.bom_id:
            warehouse_id = self.env['warehouse'].search(
                [('type', '=', 'stock')], limit=1)
            self.line_out_ids = [{'goods_id': self.goods_id.id, 'product_uos_qty': 1, 'goods_qty': 1,
                                  'warehouse_id': self.env['warehouse'].get_warehouse_by_type('production').id,
                                  'warehouse_dest_id': warehouse_id.id,
                                  'uom_id': self.goods_id.uom_id.id,
                                  'uos_id': self.goods_id.uos_id.id,
                                  'type': 'out',
                                  }]

    @api.onchange('goods_qty')
    def onchange_goods_qty(self):
        """
        改变商品数量时(wh_assembly 中的goods_qty) 根据物料清单的 数量的比例及成本价的计算
        算出新的组合件或者子件的 数量 (line.goods_qty / parent_line_goods_qty * self.goods_qty
        line.goods_qty 子件商品数量
        parent_line_goods_qty 物料清单组合件商品数量
        self.goods_qty 所要的组合件的商品数量
        line.goods_qty /parent_line_goods_qty 得出子件和组合件的比例
        line.goods_qty / parent_line_goods_qty * self.goods_qty 得出子件实际的数量的数量
        )
        :return:line_out_ids ,line_in_ids
        """
        warehouse_id = self.env['warehouse'].search(
            [('type', '=', 'stock')], limit=1)
        line_out_ids, line_in_ids = [], []
        parent_line = self.bom_id.line_parent_ids
        if warehouse_id and self.bom_id and parent_line and self.bom_id.line_child_ids:
            cost, cost_unit = parent_line.goods_id \
                .get_suggested_cost_by_warehouse(
                    warehouse_id, self.goods_qty)

            line_out_ids.append({
                'goods_id': parent_line.goods_id.id,
                'attribute_id': parent_line.attribute_id.id,
                'warehouse_id': self.env[
                    'warehouse'].get_warehouse_by_type('production').id,
                'warehouse_dest_id': warehouse_id.id,
                'uom_id': parent_line.goods_id.uom_id.id,
                'goods_qty': self.goods_qty,
                'goods_uos_qty': self.goods_qty / parent_line.goods_id.conversion,
                'uos_id': parent_line.goods_id.uos_id.id,
                'cost_unit': cost_unit,
                'cost': cost,
                'type': 'out',
            })

            line_in_ids = [{
                'goods_id': line.goods_id.id,
                'attribute_id': line.attribute_id.id,
                'warehouse_id': warehouse_id.id,
                'warehouse_dest_id': self.env[
                    'warehouse'].get_warehouse_by_type('production').id,
                'uom_id': line.goods_id.uom_id.id,
                'goods_qty': line.goods_qty / parent_line.goods_qty * self.goods_qty,
                'goods_uos_qty': line.goods_qty / parent_line.goods_qty * self.goods_qty / line.goods_id.conversion,
                'uos_id':line.goods_id.uos_id.id,
                'type': 'in',
            } for line in self.bom_id.line_child_ids]

            self.line_in_ids = False
            self.line_out_ids = False
            self.line_out_ids = line_out_ids
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
                    'attribute_id': line.attribute_id.id,
                    'warehouse_id': self.env[
                        'warehouse'].get_warehouse_by_type('production').id,
                    'warehouse_dest_id': warehouse_id.id,
                    'uom_id': line.goods_id.uom_id.id,
                    'goods_qty': line.goods_qty,
                    'goods_uos_qty': line.goods_qty / line.goods_id.conversion,
                    'uos_id': line.goods_id.uos_id.id,
                    'cost_unit': cost_unit,
                    'cost': cost,
                    'type': 'out',
                })

            line_in_ids = [{
                'goods_id': line.goods_id.id,
                'attribute_id': line.attribute_id.id,
                'warehouse_id': warehouse_id,
                'warehouse_dest_id': self.env[
                    'warehouse'].get_warehouse_by_type('production').id,
                'uom_id': line.goods_id.uom_id.id,
                'goods_qty': line.goods_qty,
                'goods_uos_qty': line.goods_qty / line.goods_id.conversion,
                'uos_id':line.goods_id.uos_id.id,
                'type': 'in',
            } for line in self.bom_id.line_child_ids]

            self.line_in_ids = False
            self.line_out_ids = False
        else:
            self.goods_qty = 1
        if len(line_out_ids) == 1 and line_out_ids:
            """当物料清单中只有一个组合件的时候,默认本单据只有一个组合件 设置is_many_to_many_combinations 为False
             使试图只能在 many2one中选择一个商品(并且只能选择在物料清单中的商品),并且回写数量"""
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


class WhBom(osv.osv):
    _name = 'wh.bom'
    _description = u'物料清单'

    BOM_TYPE = [
        ('assembly', u'组装单'),
        ('disassembly', u'拆卸单'),
        ('outsource', u'委外加工单'),
    ]

    name = fields.Char(u'物料清单名称',
                       help=u'组装/拆卸物料清单名称')
    type = fields.Selection(
        BOM_TYPE, u'类型', default=lambda self: self.env.context.get('type'),
        help=u'类型: 组装单、拆卸单')
    line_parent_ids = fields.One2many(
        'wh.bom.line', 'bom_id', u'组合件', domain=[('type', '=', 'parent')],
        context={'type': 'parent'}, copy=True,
        help=u'物料清单对应的组合件行')
    line_child_ids = fields.One2many(
        'wh.bom.line', 'bom_id', u'子件', domain=[('type', '=', 'child')],
        context={'type': 'child'}, copy=True,
        help=u'物料清单对应的子件行')
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    goods_id = fields.Many2one('goods', related='line_parent_ids.goods_id', string=u'组合商品')

    @api.one
    @api.constrains('line_parent_ids', 'line_child_ids')
    def check_parent_child_unique(self):
        """判断同一个产品不能是组合件又是子件"""
        for child_line in self.line_child_ids:
            for parent_line in self.line_parent_ids:
                if child_line.goods_id == parent_line.goods_id and child_line.attribute_id == parent_line.attribute_id:
                    raise UserError(u'组合件和子件不能相同，产品:%s' % parent_line.goods_id.name)


class WhBomLine(osv.osv):
    _name = 'wh.bom.line'
    _description = u'物料清单明细'

    BOM_LINE_TYPE = [
        ('parent', u'组合件'),
        ('child', u'子间'),
    ]

    bom_id = fields.Many2one('wh.bom', u'物料清单', ondelete='cascade',
                             help=u'子件行/组合件行对应的物料清单')
    type = fields.Selection(
        BOM_LINE_TYPE, u'类型',
        default=lambda self: self.env.context.get('type'),
        help=u'类型: 组合件、子间')
    goods_id = fields.Many2one('goods', u'商品', default=1, ondelete='restrict',
                               help=u'子件行/组合件行上的商品')
    goods_qty = fields.Float(
        u'数量', digits=dp.get_precision('Quantity'),
        default=1.0,
        help=u'子件行/组合件行上的商品数量')
    attribute_id = fields.Many2one('attribute', u'属性', ondelete='restrict')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.one
    @api.constrains('goods_qty')
    def check_goods_qty(self):
        """验证商品数量大于0"""
        if self.goods_qty <= 0:
            raise UserError(u'商品 %s 的数量必须大于0' % self.goods_id.name)