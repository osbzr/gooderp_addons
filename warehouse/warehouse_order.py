# -*- coding: utf-8 -*-

from openerp.osv import osv
from utils import inherits, inherits_after, create_name, create_origin
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api


class wh_out(models.Model):
    _name = 'wh.out'
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    TYPE_SELECTION = [
        ('inventory', u'盘亏'),
        ('others', u'其他出库'),
    ]

    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade')
    type = fields.Selection(TYPE_SELECTION, u'业务类别', default='others')
    amount_total = fields.Float(compute='_get_amount_total', string=u'合计成本金额',
                                store=True, readonly=True, digits=dp.get_precision('Amount'))

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
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    TYPE_SELECTION = [
        ('inventory', u'盘盈'),
        ('others', u'其他入库'),
    ]

    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade')
    type = fields.Selection(TYPE_SELECTION, u'业务类别', default='others')
    amount_total = fields.Float(compute='_get_amount_total', string=u'合计成本金额',
                                store=True, readonly=True, digits=dp.get_precision('Amount'))
    voucher_id = fields.Many2one('voucher', u'入库凭证',
                                 readonly=True)

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
        vouch_id = self.env['voucher'].create({'date': self.date})
        sum = 0
        for line in self.line_in_ids:
            self.env['voucher.line'].create({
                'name': self.name,
                'account_id': line.goods_id.category_id.account_id.id,
                'debit': line.cost,
                'voucher_id': vouch_id.id,
                'goods_id': line.goods_id.id,
            })
            sum += line.cost

        if self.type == 'inventory':
            account = self.env.ref('finance.small_business_chart1901')
        else:
            account = self.env.ref('finance.small_business_chart5051')

        self.env['voucher.line'].create({
            'name': self.name,
            'account_id': account.id,
            'credit': sum,
            'voucher_id': vouch_id.id,
        })

        self.voucher_id = vouch_id
        self.voucher_id.voucher_done()
        return vouch_id

    @api.one
    def delete_voucher(self):
        # 反审核入库单时删除对应的入库凭证
        if self.voucher_id:
            if self.voucher_id.state == 'done':
                self.voucher_id.voucher_draft()
            self.voucher_id.unlink()


class wh_internal(osv.osv):
    _name = 'wh.internal'
    _order = 'date DESC, id DESC'

    _inherits = {
        'wh.move': 'move_id',
    }

    move_id = fields.Many2one('wh.move', u'移库单', required=True, index=True, ondelete='cascade')
    amount_total = fields.Float(compute='_get_amount_total', string=u'合计成本金额',
                                store=True, readonly=True, digits=dp.get_precision('Amount'))

    @api.multi
    @inherits()
    def approve_order(self):
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
