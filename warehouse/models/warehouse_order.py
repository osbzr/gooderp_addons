# -*- coding: utf-8 -*-

from utils import inherits, inherits_after, create_name, create_origin
import odoo.addons.decimal_precision as dp
from odoo import models, fields, api
from odoo.exceptions import UserError


class WhOut(models.Model):
    _name = 'wh.out'
    _description = u'其他出库单'
    _inherit = ['mail.thread']
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    TYPE_SELECTION = [
        ('inventory', u'盘亏'),
        ('others', u'其他出库'),
        ('cancel', u'已作废')]

    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade',
                              help=u'其他出库单对应的移库单')
    type = fields.Selection(TYPE_SELECTION, u'业务类别', default='others',
                            help=u'类别: 盘亏,其他出库')
    amount_total = fields.Float(compute='_get_amount_total', string=u'合计成本金额',
                                store=True, readonly=True, digits=dp.get_precision(
                                    'Amount'),
                                help=u'该出库单的出库金额总和')
    voucher_id = fields.Many2one('voucher', u'出库凭证',
                                 readonly=True,
                                 help=u'该出库单的后生成的出库凭证')

    @api.multi
    @inherits_after()
    def approve_order(self):
        for order in self:
            if order.state == 'done':
                raise UserError(u'请不要重复出库')
            voucher = order.create_voucher()
            order.write({
                'voucher_id': voucher and voucher[0] and voucher[0].id,
                'state': 'done',
            })
        return True

    @api.multi
    @inherits()
    def cancel_approved_order(self):
        for order in self:
            if order.state == 'draft':
                raise UserError(u'请不要重复撤销')
            order.delete_voucher()
            order.state = 'draft'
        return True

    @api.multi
    @inherits()
    def unlink(self):
        for order in self:
            return order.move_id.unlink()

    @api.one
    @api.depends('line_out_ids.cost')
    def _get_amount_total(self):
        self.amount_total = sum(line.cost for line in self.line_out_ids)

    def get_move_origin(self, vals):
        return self._name + '.' + vals.get('type')

    @api.model
    @create_name
    @create_origin
    def create(self, vals):
        return super(WhOut, self).create(vals)

    @api.multi
    @api.onchange('type')
    def onchange_type(self):
        self.warehouse_dest_id = self.env['warehouse'].get_warehouse_by_type(
            self.type)

    def goods_inventory(self, vals):
        """
        审核时若仓库中商品不足，则产生补货向导生成其他入库单并审核。
        :param vals: 创建其他入库单需要的字段及取值信息构成的字典
        :return:
        """
        auto_in = self.env['wh.in'].create(vals)
        self.with_context({'wh_in_line_ids': [line.id for line in
                                              auto_in.line_in_ids]}).approve_order()

    @api.one
    def create_voucher(self):
        '''
        其他出库单生成出库凭证
        借：如果出库类型为盘亏，取科目 1901 待处理财产损益；如果为其他，取核算类别的会计科目
        贷：库存商品（商品分类上会计科目）
        '''
        voucher = self.env['voucher'].create({'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        credit_sum = 0  # 贷方之和
        for line in self.line_out_ids:
            if line.cost:   # 贷方行（多行）
                self.env['voucher.line'].create({
                    'name': u'%s %s' % (self.name, self.note or ''),
                    'account_id': line.goods_id.category_id.account_id.id,
                    'credit': line.cost,
                    'voucher_id': voucher.id,
                    'goods_id': line.goods_id.id,
                    'goods_qty': line.goods_qty,
                })
            credit_sum += line.cost
        account = self.type == 'inventory' \
            and self.env.ref('finance.small_business_chart1901') \
            or self.finance_category_id.account_id
        if credit_sum:  # 借方行（汇总一行）
            self.env['voucher.line'].create({
                'name': u'%s %s' % (self.name, self.note or ''),
                'account_id': account.id,
                'debit': credit_sum,
                'voucher_id': voucher.id,
            })
        if len(voucher.line_ids) > 0:
            voucher.voucher_done()
            return voucher
        else:
            voucher.unlink()

    @api.one
    def delete_voucher(self):
        # 反审核其他出库单时删除对应的出库凭证
        voucher = self.voucher_id
        if voucher.state == 'done':
            voucher.voucher_draft()

        voucher.unlink()


class WhIn(models.Model):
    _name = 'wh.in'
    _description = u'其他入库单'
    _inherit = ['mail.thread']
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    TYPE_SELECTION = [
        ('inventory', u'盘盈'),
        ('others', u'其他入库'),
    ]

    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade',
                              help=u'其他入库单对应的移库单')
    type = fields.Selection(TYPE_SELECTION, u'业务类别', default='others',
                            help=u'类别: 盘盈,其他入库,初始')
    amount_total = fields.Float(compute='_get_amount_total', string=u'合计成本金额',
                                store=True, readonly=True, digits=dp.get_precision(
                                    'Amount'),
                                help=u'该入库单的入库金额总和')
    voucher_id = fields.Many2one('voucher', u'入库凭证',
                                 readonly=True,
                                 help=u'该入库单确认后生成的入库凭证')
    is_init = fields.Boolean(u'初始化单')

    @api.multi
    @inherits()
    def approve_order(self):
        for order in self:
            if order.state == 'done':
                raise UserError(u'请不要重复入库')
            voucher = order.create_voucher()
            order.write({
                'voucher_id': voucher and voucher[0] and voucher[0].id,
                'state': 'done',
            })
        return True

    @api.multi
    @inherits()
    def cancel_approved_order(self):
        for order in self:
            if order.state == 'draft':
                raise UserError(u'请不要重复撤销')
            order.delete_voucher()
            order.state = 'draft'
        return True

    @api.multi
    @inherits()
    def unlink(self):
        for order in self:
            return order.move_id.unlink()

    @api.one
    @api.depends('line_in_ids.cost')
    def _get_amount_total(self):
        self.amount_total = sum(line.cost for line in self.line_in_ids)

    def get_move_origin(self, vals):
        return self._name + '.' + vals.get('type')

    @api.model
    @create_name
    @create_origin
    def create(self, vals):
        return super(WhIn, self).create(vals)

    @api.multi
    @api.onchange('type')
    def onchange_type(self):
        self.warehouse_id = self.env['warehouse'].get_warehouse_by_type(
            self.type).id

    @api.one
    def create_voucher(self):
        # 入库单生成入库凭证
        '''
        借：商品分类对应的会计科目 一般是库存商品
        贷：如果入库类型为盘盈，取科目 1901 待处理财产损益（暂时写死）
        如果入库类型为其他，取收发类别的会计科目
        '''

        # 初始化单的话，先找是否有初始化凭证，没有则新建一个
        if self.is_init:
            vouch_id = self.env['voucher'].search([('is_init', '=', True)])
            if not vouch_id:
                vouch_id = self.env['voucher'].create({'date': self.date,
                                                       'is_init': True,
                                                       'ref': '%s,%s' % (self._name, self.id)})
        else:
            vouch_id = self.env['voucher'].create({'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        debit_sum = 0
        for line in self.line_in_ids:
            init_obj = self.is_init and 'init_warehouse - %s' % (self.id) or ''
            if line.cost:
                self.env['voucher.line'].create({
                    'name': u'%s %s' % (self.name, self.note or ''),
                    'account_id': line.goods_id.category_id.account_id.id,
                    'debit': line.cost,
                    'voucher_id': vouch_id.id,
                    'goods_id': line.goods_id.id,
                    'goods_qty': line.goods_qty,
                    'init_obj': init_obj,
                })
            debit_sum += line.cost

        # 贷方科目： 如果是盘盈则取主营业务成本，否则取收发类别上的科目
        account = self.type == 'inventory' \
            and self.env.ref('finance.small_business_chart1901') \
            or self.finance_category_id.account_id

        if not self.is_init:
            if debit_sum:
                self.env['voucher.line'].create({
                    'name': u'%s %s' % (self.name, self.note or ''),
                    'account_id': account.id,
                    'credit': debit_sum,
                    'voucher_id': vouch_id.id,
                })
        if not self.is_init:
            if len(vouch_id.line_ids) > 0:
                vouch_id.voucher_done()
                return vouch_id
            else:
                vouch_id.unlink()
        else:
            return vouch_id

    @api.one
    def delete_voucher(self):
        # 反审核入库单时删除对应的入库凭证
        if self.voucher_id:
            if self.voucher_id.state == 'done':
                self.voucher_id.voucher_draft()
            voucher = self.voucher_id
            # 始初化单反审核只删除明细行
            if self.is_init:
                vouch_obj = self.env['voucher'].search(
                    [('id', '=', voucher.id)])
                vouch_obj_lines = self.env['voucher.line'].search([
                    ('voucher_id', '=', vouch_obj.id),
                    ('goods_id', 'in', [
                     line.goods_id.id for line in self.line_in_ids]),
                    ('init_obj', '=', 'init_warehouse - %s' % (self.id)), ])
                for vouch_obj_line in vouch_obj_lines:
                    vouch_obj_line.unlink()
            else:
                voucher.unlink()


class WhInternal(models.Model):
    _name = 'wh.internal'
    _description = u'内部调拨单'
    _inherit = ['mail.thread']
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade',
                              help=u'调拨单对应的移库单')
    amount_total = fields.Float(compute='_get_amount_total', string=u'合计成本金额',
                                store=True, readonly=True, digits=dp.get_precision(
                                    'Amount'),
                                help=u'该调拨单的出库金额总和')

    def goods_inventory(self, vals):
        """
        审核时若仓库中商品不足，则产生补货向导生成其他入库单并审核。
        :param vals: 创建其他入库单需要的字段及取值信息构成的字典
        :return:
        """
        auto_in = self.env['wh.in'].create(vals)
        self.with_context({'wh_in_line_ids': [line.id for line in
                                              auto_in.line_in_ids]}).approve_order()

    @api.multi
    @inherits()
    def approve_order(self):
        for order in self:
            if order.state == 'done':
                raise UserError(u'请不要重复入库')
            if self.env.user.company_id.is_enable_negative_stock:
                result_vals = self.env['wh.move'].create_zero_wh_in(
                    self, self._name)
                if result_vals:
                    return result_vals
            order.state = 'done'
        return True

    @api.multi
    @inherits()
    def cancel_approved_order(self):
        for order in self:
            if order.state == 'draft':
                raise UserError(u'请不要重复撤销')
            order.state = 'draft'
        return True

    @api.multi
    @inherits()
    def unlink(self):
        for order in self:
            return order.move_id.unlink()

    @api.one
    @api.depends('line_out_ids.cost')
    def _get_amount_total(self):
        self.amount_total = sum(line.cost for line in self.line_out_ids)

    @api.model
    @create_name
    @create_origin
    def create(self, vals):
        return super(WhInternal, self).create(vals)
