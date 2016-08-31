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
