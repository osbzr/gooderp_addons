# -*- coding: utf-8 -*-

from utils import inherits, inherits_after, create_name, create_origin
import odoo.addons.decimal_precision as dp
from odoo import models, fields, api

class wh_out(models.Model):
    _name = 'wh.out'
    _description = u'其他出库单'
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    TYPE_SELECTION = [
        ('inventory', u'盘亏'),
        ('others', u'其他出库'),
    ]

    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade',
                              help=u'其他出库单对应的移库单')
    type = fields.Selection(TYPE_SELECTION, u'业务类别', default='others',
                            help=u'类别: 盘亏,其他出库')
    amount_total = fields.Float(compute='_get_amount_total', string=u'合计成本金额',
                                store=True, readonly=True, digits=dp.get_precision('Amount'),
                                help=u'该出库单的出库金额总和')

    @api.multi
    @inherits(res_back=False)
    def approve_order(self):
        return True

    @api.multi
    @inherits()
    def cancel_approved_order(self):
        return True

    @api.multi
    @inherits_after()
    def unlink(self):
        return super(wh_out, self).unlink()

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
        return super(wh_out, self).create(vals)

    @api.multi
    @api.onchange('type')
    def onchange_type(self):
        self.warehouse_dest_id = self.env['warehouse'].get_warehouse_by_type(self.type)

class wh_in(models.Model):
    _name = 'wh.in'
    _description = u'其他入库单'
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
                                store=True, readonly=True, digits=dp.get_precision('Amount'),
                                help=u'该入库单的入库金额总和')
    voucher_id = fields.Many2one('voucher', u'入库凭证',
                                 readonly=True,
                                 help=u'该入库单的审核后生成的入库凭证')
    is_init = fields.Boolean(u'初始化单')


    @api.multi
    @inherits()
    def approve_order(self):
        self.create_voucher()
        return True

    @api.multi
    @inherits()
    def cancel_approved_order(self):
        self.delete_voucher()
        return True

    @api.multi
    @inherits_after()
    def unlink(self):
        return super(wh_in, self).unlink()

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
        return super(wh_in, self).create(vals)

    @api.multi
    @api.onchange('type')
    def onchange_type(self):
        self.warehouse_id = self.env['warehouse'].get_warehouse_by_type(self.type).id

    @api.one
    def create_voucher(self):
        # 入库单生成入库凭证
        '''
        借：商品分类对应的会计科目 一般是库存商品
        贷：如果入库类型为盘盈，取科目 1901 待处理财产损益（暂时写死）
        如果入库类型为其他，取科目 5051 其他业务收入
        '''

        # 初始化单的话，先找是否有初始化凭证，没有则新建一个
        if self.is_init:
            vouch_id = self.env['voucher'].search([('is_init', '=', True)])
            if not vouch_id:
                vouch_id = self.env['voucher'].create({'date': self.date})
                vouch_id.is_init = True
        else:
            vouch_id = self.env['voucher'].create({'date': self.date})
        self.voucher_id = vouch_id
        debit_sum = 0
        for line in self.line_in_ids:
            init_obj = self.is_init and 'init_warehouse - %s' % (self.id) or ''
            if line.cost:
                self.env['voucher.line'].create({
                    'name': self.name,
                    'account_id': line.goods_id.category_id.account_id.id,
                    'debit': line.cost,
                    'voucher_id': vouch_id.id,
                    'goods_id': line.goods_id.id,
                    'init_obj': init_obj,
                })
            debit_sum += line.cost

        # 贷方科目： 主营业务成本
        account = self.env.ref('finance.account_cost')

        if not self.is_init:
            if debit_sum:
                self.env['voucher.line'].create({
                    'name': self.name,
                    'account_id': account.id,
                    'credit': debit_sum,
                    'voucher_id': vouch_id.id,
                    })
        if not self.is_init :
            if len(self.voucher_id.line_ids) > 0:
                self.voucher_id.voucher_done()
            else:
                self.voucher_id.unlink()
        return vouch_id

    @api.one
    def delete_voucher(self):
        # 反审核入库单时删除对应的入库凭证
        if self.voucher_id:
            if self.voucher_id.state == 'done':
                self.voucher_id.voucher_draft()
            voucher, self.voucher_id = self.voucher_id, False
            #始初化单反审核只删除明细行
            if self.is_init:
                vouch_obj = self.env['voucher'].search([('id', '=', voucher.id)])
                vouch_obj_lines = self.env['voucher.line'].search([
                    ('voucher_id', '=', vouch_obj.id),
                    ('goods_id', 'in', [line.goods_id.id for line in self.line_in_ids]),
                    ('init_obj', '=', 'init_warehouse- %s' % (self.id)),])
                for vouch_obj_line in vouch_obj_lines:
                    vouch_obj_line.unlink()
            else:
                voucher.unlink()


class wh_internal(models.Model):
    _name = 'wh.internal'
    _description = u'内部调拨单'
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade',
                              help=u'调拨单对应的移库单')
    amount_total = fields.Float(compute='_get_amount_total', string=u'合计成本金额',
                                store=True, readonly=True, digits=dp.get_precision('Amount'),
                                help=u'该调拨单的出库金额总和')


    def goods_inventory(self, vals):
        auto_in = self.env['wh.in'].create(vals)
        self.with_context({'wh_in_line_ids': [line.id for line in
                                              auto_in.line_in_ids]}).approve_order()

    @api.multi
    @inherits()
    def approve_order(self):
        if self.env.user.company_id.is_enable_negative_stock:
            result_vals = self.env['wh.move'].create_zero_wh_in(self, self._name)
            if result_vals:
                return result_vals
        return True

    @api.multi
    @inherits()
    def cancel_approved_order(self):
        return True

    @api.multi
    @inherits_after()
    def unlink(self):
        return super(wh_internal, self).unlink()

    @api.one
    @api.depends('line_out_ids.cost')
    def _get_amount_total(self):
        self.amount_total = sum(line.cost for line in self.line_out_ids)

    @api.model
    @create_name
    @create_origin
    def create(self, vals):
        return super(wh_internal, self).create(vals)
