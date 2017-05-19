# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

class location(models.Model):
    _name = 'location'
    name = fields.Char(u'货位号', required=True)
    warehouse_id = fields.Many2one('warehouse', string='仓库')
    goods_id = fields.Many2one('goods', u'商品')
    #parent_location_id = fields.Many2one('location', string='父级库位')
    #child_location_ids = fields.One2many('location', 'parent_location_id', string='子库位列表')

class goods(models.Model):
    _inherit = 'goods'
    loc_ids = fields.One2many('location', 'goods_id', string='库位')


class wh_move_line(models.Model):
    _inherit = 'wh.move.line'
    location_id = fields.Many2one('location', string='库位')


class wave(models.Model):
    _name = "wave"
    _description = u"用来分类报表,让相似的报表显示在一起"

    state = fields.Selection([('draft', '未打印'), ('printed', '已打印'), ('done', '已完成')], string='状态')
    express_type = fields.Selection([('SF', u'顺丰'), ('YTO', u'圆通')], string='承运商', default='SF')
    name = fields.Char(u'单号', help=u'用来')
    order_type = fields.Char(u'订单类型', default='客户订单')
    user_id = fields.Many2one('res.users', u'创建人')
    line_ids = fields.One2many('wave.line', 'wave_id', string='任务行')
    orgin_ids = fields.One2many('sell.delivery', 'wave_id', string='发货单列表')


class sell_delivery(models.Model):
    _inherit = 'sell.delivery'

    wave_id = fields.Many2one('wave', string='捡货单')
    pakge_sequence = fields.Integer(u'打包序号')


class wave_line(models.Model):
    _name = "wave.line"
    _description = u"用来分类报表,让相似的报表显示在一起"

    wave_id = fields.Many2one('wave', string='总包')
    sequence = fields.Integer(u'序号', readonly=1)
    goods_id = fields.Many2one('goods', string='商品')
    location_id = fields.Many2one('location', string='库位号')
    picking_num = fields.Integer(u'捡货数量')
    page_num_list = fields.Text(u'格子数')
    page_qty_list = fields.Text(u'对应数量')
    move_line_ids = fields.Many2many('wh.move.line', 'wave_move_rel', \
                                     'wave_line_id', 'move_line_id', string='发货单行')
    goods_code = fields.Char(related='goods_id.code', relation='goods', string='货品代码', readonly=1)
    barcode = fields.Char(related='goods_id.barcode', relation='goods', string='货品条码', readonly=1)

class create_wave(models.Model):

    _name = "create.wave"

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
        :param view_id:
        :param view_type:
        :param toolbar:
        :param submenu:
        :return:
        """
        res = super(create_wave, self).fields_view_get(view_id, view_type,
                                                         toolbar=toolbar, submenu=False)
        for wave_row in self.env['sell.delivery'].browse(self.env.context.get('active_ids')):
            if wave_row.wave_id:
                raise UserError(u'请不要重复生成分拣单!')
        return res

    @api.multi
    def set_default_note(self):
        context = self.env.context
        all_delivery_name = [delivery.name for delivery in
                             self.env['sell.delivery'].browse(context.get('active_ids'))]
        return '-'.join(all_delivery_name)

    note = fields.Char(u'本次处理发货单', default=set_default_note, readonly=True)
    express_type = fields.Selection([('SF', u'顺丰'), ('ZT', u'中通')], string='承运商')


    def contract_wave_line_data(self, product_location_num_dict):
        return_line_data = []
        sequence = 1
        for key, val  in product_location_num_dict.iteritems():
            goods_id, location_id = key
            page_num_list, page_qty_list, delivery_lines, picking_num = '', '', [], 0
            for line_id, goods_qty, packge in val:
                page_num_list += "(%s)\n"%(packge)
                page_qty_list += "%s\n"%(goods_qty)
                delivery_lines.append((4, line_id))
                picking_num += goods_qty
            return_line_data.append({
                'sequence':sequence,
                'goods_id':goods_id,
                'picking_num':picking_num,
                'location_id':location_id,
                'page_qty_list':page_qty_list,
                'page_num_list':page_num_list,
                'move_line_ids': delivery_lines,
            })
            sequence += 1
        return return_line_data

    @api.multi
    def create_package(self):
        """
        """
        context = self.env.context
        product_location_num_dict = {}
        index = 1
        wave_row = self.env['wave'].create({'user_id': self.env.uid})
        for delivery_row in self.env['sell.delivery'].browse(context.get('active_ids')):
            delivery_row.pakge_sequence = index
            delivery_row.wave_id = wave_row.id
            for line in delivery_row.line_out_ids:
                if (line.goods_id.id, line.location_id.id) in product_location_num_dict:
                    product_location_num_dict[(line.goods_id.id, line.location_id.id)].append(
                        (line.id, line.goods_qty, index))
                else:
                    product_location_num_dict[(line.goods_id.id, line.location_id.id)] =\
                     [(line.id, line.goods_qty, index)]
            index += 1
        wave_row.line_ids = self.contract_wave_line_data(product_location_num_dict)
        print product_location_num_dict
        return {'type': 'ir.actions.act_window',
                'res_model': 'wave',
                'view_mode': 'form',
                'views': [(False, 'form'), (False, 'tree')],
                'res_id': wave_row.id,
                'target': 'current',
                'flags': {'form': {'action_buttons': True}}}
