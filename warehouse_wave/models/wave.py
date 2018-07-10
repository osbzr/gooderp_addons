# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class Wave(models.Model):
    _name = "wave"
    _description = u"拣货单"
    _order = 'create_date desc'

    state = fields.Selection([('draft', '未打印'), ('printed', '已打印'),
                              ('done', '已完成')], string='状态', default='draft',
                             index=True,
                             )
    express_type = fields.Char(string='承运商')
    name = fields.Char(u'单号')
    order_type = fields.Char(u'订单类型', default=u'客户订单')
    line_ids = fields.One2many('wave.line', 'wave_id', string='任务行')

    @api.multi
    def print_express_menu(self):
        ''' 打印快递面单 '''
        move_rows = self.env['wh.move'].search([('wave_id', '=', self.id)])
        return {'type': 'ir.actions.client',
                'tag': 'warehouse_wave.print_express_menu',
                'context': {'move_ids': [move.id for move in move_rows]},
                'target': 'new',
                }

    @api.multi
    def print_package_list(self):
        ''' 打印装箱单 '''
        move_rows = self.env['wh.move'].search([('wave_id', '=', self.id)])
        return {'type': 'ir.actions.client',
                'tag': 'warehouse_wave.print_express_package',
                'context': {'move_ids': [move.id for move in move_rows]},
                'target': 'new',
                }

    @api.multi
    def report_wave(self):
        ''' 打印拣货单 '''
        assert len(self._ids) == 1

        records = self.env['wave'].browse(self.id)
        if records[0].state == 'draft':
            records[0].state = 'printed'

        return self.env['report'].get_action(self, 'warehouse_wave.report_wave_view')

    @api.multi
    def delivery_list(self):
        for wave in self:
            delivery_lists = self.env['sell.delivery'].search([('wave_id', '=', wave.id)])
            view_id = self.env.ref('sell.sell_delivery_tree').id
            return {
                'name': u'销售发货单',
                'view_type': 'form',
                'view_mode': 'tree',
                'view_id': False,
                'views': [(view_id, 'tree')],
                'res_model': 'sell.delivery',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [delivery.id for delivery in delivery_lists])],
                'target': 'current',
            }

    @api.multi
    def unlink(self):
        """
        1.有部分已经打包,拣货单不能进行删除
        2.能删除了,要把一些相关联的字段清空 如pakge_sequence
        """
        for wave_row in self:
            wh_move_rows = self.env['wh.move'].search([('wave_id', '=', wave_row.id),
                                                       ('state', '=', 'done')])
            if wh_move_rows:
                raise UserError(u"""发货单%s已经打包发货,拣货单%s不允许删除!
                                 """ % (u'-'.join([move_row.name for move_row in wh_move_rows]),
                                        wave_row.name))
            # 清空发货单上的格子号
            move_rows = self.env['wh.move'].search(
                [('wave_id', '=', wave_row.id)])
            move_rows.write({'pakge_sequence': False})
        return super(Wave, self).unlink()


class WhMove(models.Model):
    _name = 'wh.move'
    _inherit = ['wh.move', 'state.city.county']

    wave_id = fields.Many2one('wave', string=u'拣货单')
    pakge_sequence = fields.Char(u'格子号')

    @api.multi
    def unlink(self):
        """
        删除发货单时，删除对应的拣货单行
        """
        for move in self:
            for wave_line in move.wave_id.line_ids:
                for move_line in wave_line.move_line_ids:
                    if move_line.move_id.id == move.id:
                        move_line.unlink()

        return super(WhMove, self).unlink()


class WaveLine(models.Model):
    _name = "wave.line"
    _description = u"拣货单行"
    _order = 'location_text'

    wave_id = fields.Many2one('wave', ondelete='cascade', string=u'拣货单')
    goods_id = fields.Many2one('goods', string=u'商品')
    attribute_id = fields.Many2one('attribute', string=u'属性')
    line_location_ids = fields.One2many('wave.line.location',
                                        'wave_line_id', string=u'库位')
    picking_qty = fields.Integer(u'拣货数量')
    move_line_ids = fields.Many2many('wh.move.line', 'wave_move_rel',
                                     'wave_line_id', 'move_line_id', string=u'发货单行')
    location_text = fields.Char(u'库位序列')


class WaveLineLocation(models.Model):
    _name = "wave.line.location"
    _description = u"拣货单行上的库位"
    _order = 'location_id'

    wave_line_id = fields.Many2one('wave.line',
                                   ondelete='cascade', string=u'拣货单行')
    location_id = fields.Many2one('location', string=u'库位')
    picking_qty = fields.Integer(u'拣货数量')


class CreateWave(models.TransientModel):

    _name = "create.wave"

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
        根据内容判断 报出错误
        """
        model = self.env.context.get('active_model')
        res = super(CreateWave, self).fields_view_get(view_id, view_type,
                                                      toolbar=toolbar, submenu=False)
        model_rows = self.env[model].browse(self.env.context.get('active_ids'))
        express_type = model_rows[0].express_type
        wh_id = model_rows[0].warehouse_id.id
        for model_row in model_rows:
            if model_row.wave_id:
                raise UserError(u'请不要重复生成拣货单!')
            if express_type and express_type != model_row.express_type:
                raise UserError(u'发货方式不一样的发货单不能生成同一拣货单!')
            if wh_id and wh_id != model_row.warehouse_id.id:
                raise UserError(u'不同仓库的发货单不能生成同一拣货单!')
        return res

    @api.multi
    def set_default_note(self):
        """
        设置默认值, 用来确认要生成拣货单的 发货单据编码
        """
        context = self.env.context
        all_delivery_name = [delivery.name for delivery in
                             self.env['sell.delivery'].browse(context.get('active_ids'))]
        return '-'.join(all_delivery_name)

    note = fields.Char(u'本次处理发货单', default=set_default_note, readonly=True)
    active_model = fields.Char(
        u'当前模型', default=lambda self: self.env.context.get('active_model'))

    def build_wave_line_data(self, product_location_num_dict):
        """
        构造拣货单行的 数据
        """
        return_line_data = []
        sequence = 1
        for key, val in product_location_num_dict.iteritems():
            goods_id, attribute_id = key
            delivery_lines, picking_qty = [], 0
            for line_id, goods_qty in val:
                delivery_lines.append((4, line_id))
                picking_qty += goods_qty
            return_line_data.append({
                'goods_id': goods_id,
                'picking_qty': picking_qty,
                'move_line_ids': delivery_lines,
            })
            sequence += 1
        return return_line_data

    @api.multi
    def create_wave_reserved(self, wave_row, line):
        reserved_dict = {
            'wave_id': wave_row.id,
            'goods_id': line.goods_id.id,
            'attribute_id': line.attribute_id.id,
            'warehouse_id': line.warehouse_id.id,
            'goods_qty': line.goods_qty,
            'move_id': line.move_id.id,
            'move_name': line.move_id.name,
        }
        return reserved_dict

    @api.multi
    def get_sell_delivery(self, goods_id, attribute_id):
        ''' 查找缺货发货单 '''
        sell_delivery_lists = []
        for active_model in self.env[self.active_model].browse(self.env.context.get('active_ids')):
            for line in active_model.line_out_ids:
                if line.goods_id.id == goods_id and line.attribute_id.id == attribute_id:
                    sell_delivery_lists.append(line.move_id.name)

        return sell_delivery_lists

    @api.multi
    def create_wave(self):
        """
        创建拣货单
        """
        warehouse_id = False
        context = self.env.context
        product_location_num_dict = {}
        index = 0
        express_type = ''  # 快递方式
        wave_row = self.env['wave'].create({})
        for active_model in self.env[self.active_model].browse(context.get('active_ids')):
            if not active_model.express_type:
                raise UserError(u'请先输入%s的承运商' % active_model.name)
            available_line = []
            for line in active_model.line_out_ids:
                if not warehouse_id:
                    warehouse_id = line.warehouse_id.id

                if line.goods_id.no_stock:
                    continue

                # 生成未发货的 wave.line 对应的记录到 wave.reserved
                reserved_dict = self.create_wave_reserved(wave_row, line)
                self.env['wave.reserved'].create(reserved_dict)
                reserved_waves = self.env['wave.reserved'].search([('goods_id', '=', line.goods_id.id),
                                                                   ('attribute_id', '=', line.attribute_id.id),
                                                                   ('warehouse_id', '=', line.warehouse_id.id)])
                total_goods_qty = sum(line_rec.goods_qty for line_rec in reserved_waves)

                result = line.move_id.check_goods_qty(
                    line.goods_id, line.attribute_id, line.warehouse_id)
                result = result[0] or 0
                if total_goods_qty > result:
                    # 缺货发货单不分配进拣货单
                    available_line.append(False)
                    # 查找所有勾选的 含有该产品的 发货单
                    deliverys_lists = self.get_sell_delivery(line.goods_id.id, line.attribute_id.id)

                    raise UserError(u'您勾选的订单与未发货的拣货单商品数量总和大于库存，不能生成拣货单。\n'
                                    u'产品 %s 库存不足。\n'
                                    u'相关拣货单 %s' % (line.goods_id.name, deliverys_lists))
                else:
                    available_line.append(True)

            if all(available_line):
                for line in active_model.line_out_ids:
                    if (line.goods_id.id, line.attribute_id.id) in product_location_num_dict:
                        product_location_num_dict[(line.goods_id.id, line.attribute_id.id)].append(
                            (line.id, line.goods_qty))
                    else:
                        product_location_num_dict[(line.goods_id.id, line.attribute_id.id)] =\
                            [(line.id, line.goods_qty)]

                index += 1
                active_model.pakge_sequence = index
                active_model.wave_id = wave_row.id
                express_type = active_model.express_type

        # 所有订单都不缺货
        wave_row.express_type = express_type
        wave_row.line_ids = self.build_wave_line_data(
            product_location_num_dict)

        # 给拣货单行添加库位
        for WaveLine in wave_row.line_ids:
            location_text = ''
            # 找到产品、属性、仓库满足的库位
            available_locs = self.env['location'].search([('goods_id', '=', WaveLine.goods_id.id),
                                                          ('attribute_id', '=',
                                                           WaveLine.attribute_id.id),
                                                          ('warehouse_id', '=', warehouse_id),
                                                          ('save_qty', '!=', 0)])
            remaining_picking_qty = WaveLine.picking_qty
            for loc in available_locs:
                if remaining_picking_qty < 0:
                    break
                # 剩余拣货数量 大于 当前遍历库位数量，拣货数量取当前遍历库位数量，否则取剩余拣货数量
                if remaining_picking_qty > loc.current_qty:
                    picking_qty = loc.current_qty
                else:
                    picking_qty = remaining_picking_qty

                self.env['wave.line.location'].create({
                    'wave_line_id': WaveLine.id,
                    'location_id': loc.id,
                    'picking_qty': picking_qty
                })
                remaining_picking_qty -= loc.current_qty
                location_text += loc.name + ','
            WaveLine.location_text = location_text

        return {'type': 'ir.actions.act_window',
                'res_model': 'wave',
                'name': u'拣货单',
                'view_mode': 'form',
                'views': [(False, 'tree')],
                'res_id': wave_row.id,
                'target': 'current'}


class DoPack(models.Model):
    _name = 'do.pack'
    _rec_name = 'odd_numbers'
    odd_numbers = fields.Char(u'单号')
    product_line_ids = fields.One2many('pack.line', 'pack_id', string='商品行')
    is_pack = fields.Boolean(
        compute='compute_is_pack_ok', string='打包完成', store=True)

    @api.multi
    def unlink(self):
        for pack in self:
            if pack.is_pack:
                raise UserError(u'已完成打包记录不能删除!')
        return super(DoPack, self).unlink()

    @api.one
    @api.depends('product_line_ids.goods_qty', 'product_line_ids.pack_qty')
    def compute_is_pack_ok(self):
        """计算字段, 看看是否打包完成"""
        if self.product_line_ids:
            self.is_pack = True
        for line in self.product_line_ids:
            if line.goods_qty != line.pack_qty:
                self.is_pack = False

        if self.is_pack:
            # 打包完成，清空 wave.reserved 表上的记录
            reserved_waves = self.env['wave.reserved'].search([('move_name', '=', self.odd_numbers)])
            reserved_waves.unlink()

            ORIGIN_EXPLAIN = {
                'wh.internal': 'wh.internal',
                'wh.out.others': 'wh.out',
                'buy.receipt.return': 'buy.receipt',
                'sell.delivery.sell': 'sell.delivery',
            }
            function_dict = {'sell.delivery': 'sell_delivery_done',
                             'wh.out': 'approve_order'}
            move_row = self.env['wh.move'].search(
                [('name', '=', self.odd_numbers)])
            # move_row.write({'pakge_sequence': False}) # 打包完成 格子号 写成 False? 暂时注释掉
            model_row = self.env[ORIGIN_EXPLAIN.get(move_row.origin)
                                 ].search([('sell_move_id', '=', move_row.id)])
            func = getattr(model_row, function_dict.get(model_row._name), None)

            if func and model_row.state == 'draft':
                if function_dict.get(model_row._name) == 'sell_delivery_done':
                    result_vals = func()
                    # 执行 销售发货审核，允许库存为零，执行 common.dialog.wizard 里的 do_confirm 方法
                    if result_vals and isinstance(result_vals, dict) and result_vals['res_model'] == 'common.dialog.wizard':
                        # 通过 context 传值给 common.dialog.wizard
                        ctx = result_vals['context']
                        ctx['active_model'] = 'sell.delivery'
                        ctx['active_ids'] = [model_row.id]

                        # 创建 common.dialog.wizard 对象，模拟打开对象窗口时的操作，传入 active_model， active_ids
                        dialog = self.env['common.dialog.wizard'].with_context(ctx).create({
                            'message': result_vals['context']['message']
                        })
                        dialog.do_confirm()
                    # 执行完 sell_delivery_done 方法，给 打包完成 字段赋 True 值
                    self.is_pack = True

    def get_line_data(self, code):
        """构造行的数据"""
        line_data = []
        model_row = self.env['wh.move'].search([('name', '=', code)])
        for line_row in model_row.line_out_ids:
            line_data.append((0, 0, {'goods_id': line_row.goods_id.id,
                                     'goods_qty': line_row.goods_qty}))
        return line_data

    @api.multi
    def scan_barcode(self, code_str, pack_id):
        """扫描多个条码,条码的处理 拆分 """
        if code_str:
            pack_row = self.browse(pack_id)
            code_list = code_str.split(" ")
            for code in code_list:
                if pack_row.odd_numbers:
                    scan_code = code
                else:
                    move_row = self.env['wh.move'].search(
                        [('express_code', '=', code)])
                    if not move_row:
                        raise UserError(u'面单号不存在！')
                    if move_row.state == 'done':
                        raise UserError(u'发货单已经打包完成!')
                    scan_code = move_row.name
                self.scan_one_barcode(scan_code, pack_row)
                if pack_row.is_pack:
                    return 'done'
        return True

    def scan_one_barcode(self, code, pack_row):
        """对于一个条码的处理"""
        if pack_row.is_pack:
            raise UserError(u'已经打包完成!')
        if not pack_row.odd_numbers:
            line_data = self.get_line_data(code)
            if not line_data:
                raise UserError(u'请先扫描快递面单!')
            pack_row.odd_numbers = code
            pack_row.product_line_ids = line_data
        else:
            goods_row = self.env['goods'].search([('barcode', '=', code)])
            line_rows = self.env['pack.line'].search([('goods_id', '=', goods_row.id),
                                                      ('pack_id', '=', pack_row.id)])
            if not line_rows:
                raise UserError(u'商品%s不在当前要打包的发货单%s上!' % (
                    goods_row.name, pack_row.odd_numbers))
            goods_is_enough = True
            for line_row in line_rows:
                if line_row.goods_qty <= line_row.pack_qty:
                    continue

                line_row.pack_qty += 1
                goods_is_enough = False
                break

            if goods_is_enough:
                raise UserError(u'发货单%s要发货的商品%s已经充足,请核对后在进行操作!' % (
                    pack_row.odd_numbers, goods_row.name))
        return True


class PackLine(models.Model):
    _name = 'pack.line'

    pack_id = fields.Many2one('do.pack', string='打包')
    goods_id = fields.Many2one('goods', string='商品')
    goods_qty = fields.Float(u'要发货数量')
    pack_qty = fields.Float(u'打包数量')


class delivery_express_package_print(models.TransientModel):
    _name = "delivery.express.package.print"
    _description = u'销售发货单打印'
    _rec_name = 'note'

    note = fields.Char(u'说明', readonly=True)

    @api.model
    def default_get(self, fields):
        '''  '''
        defaults = {}
        if self._context.get('express_info'):
            defaults['note'] = u'打印销售发货单的快递面单'
        if self._context.get('package_info'):
            defaults['note'] = u'打印销售发货单的装箱单'
        return defaults

    @api.multi
    def button_print(self):
        ''' 打印销售发货单的快递面单、装箱单 '''
        delivery_orders = self.env['sell.delivery'].search([('id', 'in', self._context.get('active_ids'))])
        move_rows = self.env['wh.move'].search([('id', 'in', [move.sell_move_id.id for move in delivery_orders])])
        if self._context.get('express_info'):
            return {'type': 'ir.actions.client',
                    'tag': 'warehouse_wave.print_express_menu',
                    'context': {'move_ids': [move.id for move in move_rows]},
                    'target': 'current',
                    }
        if self._context.get('package_info'):
            return {'type': 'ir.actions.client',
                    'tag': 'warehouse_wave.print_express_package',
                    'context': {'move_ids': [move.id for move in move_rows]},
                    'target': 'current',
                    }


class WaveReserved(models.Model):
    _name = 'wave.reserved'
    _description = u'wave预留'

    wave_id = fields.Many2one('wave',
                              ondelete='cascade',
                              string=u'拣货单',
                              help=u'每条记录对应的拣货单ID，在创建记录完成时填入。'
                                   u'当删除wave时，级联删除预留记录。')
    goods_id = fields.Many2one('goods',
                               ondelete='restrict',
                               string=u'商品',
                               help=u'每条记录对应的商品ID，在创建记录时填入。')
    attribute_id = fields.Many2one('attribute',
                                   string=u'属性',
                                   ondelete='restrict',
                                   domain="[('goods_id', '=', goods_id)]",
                                   help=u'商品的属性。')
    warehouse_id = fields.Many2one('warehouse',
                                   string=u'仓库',
                                   ondelete='restrict',
                                   help=u'生成该记录的单据对应的仓库ID，在创建记录时填入。')
    goods_qty = fields.Float(u'数量')
    move_id = fields.Many2one('wh.move',
                              string=u'发货单',
                              ondelete='cascade',
                              help=u'每条记录对应的move ID，在创建记录时填入。'
                                   u'当删除move时，级联删除预留记录。')
    move_name = fields.Char(u'发货单号',
                            help=u'每条记录对应的发货单号，在创建记录时填入。方便在打包完成时清空记录。')
