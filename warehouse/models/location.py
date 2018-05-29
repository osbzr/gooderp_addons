# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class Location(models.Model):
    _name = 'location'
    _description = u'货位'
    _order = 'name'

    @api.multi
    def _get_current_qty(self):
        # 获取当前 库位 的商品数量
        for Location in self:
            lines = self.env['wh.move.line'].search([('goods_id', '=', Location.goods_id.id),
                                                     ('attribute_id', '=',
                                                      Location.attribute_id.id),
                                                     ('warehouse_dest_id', '=',
                                                      Location.warehouse_id.id),
                                                     ('location_id',
                                                      '=', Location.id),
                                                     ('state', '=', 'done')])
            Location.current_qty = sum([line.qty_remaining for line in lines])
            Location.write({'save_qty': Location.current_qty})
            if Location.current_qty == 0:
                Location.write({'goods_id': False, 'attribute_id': False})

    name = fields.Char(u'货位号',
                       required=True)
    warehouse_id = fields.Many2one('warehouse',
                                   string=u'仓库',
                                   required=True)
    goods_id = fields.Many2one('goods',
                               u'商品')
    attribute_id = fields.Many2one('attribute', u'属性', ondelete='restrict',
                                   help=u'商品的属性')
    current_qty = fields.Integer(u'数量',
                                 compute='_get_current_qty'
                                 )
    save_qty = fields.Float(u'在手数量')

    _sql_constraints = [
        ('wh_loc_uniq', 'unique(warehouse_id, name)', u'同仓库库位不能重名')
    ]

    @api.multi
    def change_location(self):
        for Location in self:
            view = self.env.ref('warehouse.change_location_form')
            return {
                'name': u'库位',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'change.location',
                'view_id': False,
                'views': [(view.id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {'default_from_location': Location.id},
            }


class ChangeLocation(models.TransientModel):
    _name = 'change.location'
    _description = u'货位转移'

    from_location = fields.Many2one('location', string=u'源库位', required=True)
    to_location = fields.Many2one('location', string=u'目的库位', required=True)
    change_qty = fields.Float(u'转出数量')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
        转出库位产品数量大于 0
        """
        model = self.env.context.get('active_model')
        res = super(ChangeLocation, self).fields_view_get(view_id, view_type,
                                                          toolbar=toolbar, submenu=False)
        model_rows = self.env[model].browse(self.env.context.get('active_ids'))
        for model_row in model_rows:
            if model_row.current_qty <= 0:
                raise UserError(u'转出库位产品数量不能小于等于 0')
        return res

    @api.multi
    def confirm_change(self):
        for change in self:
            if change.change_qty < 0:
                raise UserError(u'转出数量不能小于零')
            if change.from_location.id == change.to_location.id:
                raise UserError(u'转出库位 %s 与转入库位不能相同' %
                                change.from_location.name)
            if change.from_location.current_qty < change.change_qty:
                raise UserError(u'转出数量不能大于库位现有数量，库位 %s 现有数量  %s'
                                % (change.from_location.name, change.from_location.current_qty))
            # 转出库位与转入库位的 产品、产品属性要相同
            if (change.from_location.goods_id.id != change.to_location.goods_id.id and change.to_location.goods_id.id) or \
                    (change.from_location.attribute_id.id != change.to_location.attribute_id.id and change.to_location.attribute_id.id):
                raise UserError(u'请检查转出库位与转入库位的产品、产品属性是否都相同！')

            # 创建 内部移库单
            wh_internal = self.env['wh.internal'].with_context({'location': change.from_location.id}).create({
                'warehouse_id': change.from_location.warehouse_id.id,
                'warehouse_dest_id': change.to_location.warehouse_id.id,
            })
            self.env['wh.move.line'].with_context({'type': 'internal'}).create({
                'move_id': wh_internal.move_id.id,
                'goods_id': change.from_location.goods_id.id,
                'attribute_id': change.from_location.attribute_id.id,
                'goods_qty': change.change_qty,
                'location_id': change.to_location.id,
            })
            # 自动审核 内部移库单
            wh_internal.approve_order()

            # 返回 更新产品数量后的 库位列表
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
