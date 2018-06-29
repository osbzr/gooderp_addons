# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class WhMove(models.Model):
    _name = 'wh.move'
    _description = u'移库单'

    MOVE_STATE = [
        ('draft', u'草稿'),
        ('done', u'已完成'),
        ('cancel', u'已作废'),]

    @api.one
    @api.depends('line_out_ids', 'line_in_ids')
    def _compute_total_qty(self):
        goods_total = 0
        if self.line_in_ids:
            # 入库商品总数
            goods_total = sum(line.goods_qty for line in self.line_in_ids)
        elif self.line_out_ids:
            # 出库商品总数
            goods_total = sum(line.goods_qty for line in self.line_out_ids)
        self.total_qty = goods_total

    @api.model
    def _get_default_warehouse_impl(self):
        if self.env.context.get('warehouse_type', 'stock'):
            return self.env['warehouse'].get_warehouse_by_type(
                self.env.context.get('warehouse_type', 'stock'))

    @api.model
    def _get_default_warehouse_dest_impl(self):
        if self.env.context.get('warehouse_dest_type', 'stock'):
            return self.env['warehouse'].get_warehouse_by_type(
                self.env.context.get('warehouse_dest_type', 'stock'))

    @api.model
    def _get_default_warehouse(self):
        '''获取调出仓库'''
        return self._get_default_warehouse_impl()

    @api.model
    def _get_default_warehouse_dest(self):
        '''获取调入仓库'''
        return self._get_default_warehouse_dest_impl()

    origin = fields.Char(u'移库类型', required=True,
                         help=u'移库类型')
    name = fields.Char(u'单据编号', copy=False, default='/',
                       help=u'单据编号，创建时会自动生成')
    ref = fields.Char(u'外部单号')
    state = fields.Selection(MOVE_STATE, u'状态', copy=False, default='draft',
                             index=True,
                             help=u'移库单状态标识，新建时状态为草稿;确认后状态为已确认',
                             track_visibility='onchange')
    partner_id = fields.Many2one('partner', u'业务伙伴', ondelete='restrict',
                                 help=u'该单据对应的业务伙伴')
    date = fields.Date(u'单据日期', required=True, copy=False, default=fields.Date.context_today,
                       help=u'单据创建日期，默认为当前天')
    warehouse_id = fields.Many2one('warehouse', u'调出仓库',
                                   ondelete='restrict',
                                   required=True,
                                   readonly=True,
                                   domain="['|',('user_ids','=',False),('user_ids','in',uid)]",
                                   states={'draft': [('readonly', False)]},
                                   default=_get_default_warehouse,
                                   help=u'移库单的来源仓库')
    warehouse_dest_id = fields.Many2one('warehouse', u'调入仓库',
                                        ondelete='restrict',
                                        required=True,
                                        readonly=False,
                                        domain="['|',('user_ids','=',False),('user_ids','in',uid)]",
                                        states={'done': [('readonly', True)]},
                                        default=_get_default_warehouse_dest,
                                        help=u'移库单的目的仓库')
    approve_uid = fields.Many2one('res.users', u'确认人',
                                  copy=False, ondelete='restrict',
                                  help=u'移库单的确认人')
    approve_date = fields.Datetime(u'确认日期', copy=False)
    line_out_ids = fields.One2many('wh.move.line', 'move_id', u'出库明细',
                                   domain=[
                                       ('type', 'in', ['out', 'internal'])],
                                   copy=True,
                                   help=u'出库类型的移库单对应的出库明细')
    line_in_ids = fields.One2many('wh.move.line', 'move_id', u'入库明细',
                                  domain=[('type', '=', 'in')],
                                  context={'type': 'in'}, copy=True,
                                  help=u'入库类型的移库单对应的入库明细')
    note = fields.Text(u'备注',
                       copy=False,
                       help=u'可以为该单据添加一些需要的标识信息')
    total_qty = fields.Integer(u'商品总数', compute=_compute_total_qty, store=True,
                               help=u'该移库单的入/出库明细行包含的商品总数')
    user_id = fields.Many2one(
        'res.users',
        u'经办人',
        ondelete='restrict',
        states={'done': [('readonly', True)]},
        default=lambda self: self.env.user,
        help=u'单据经办人',
        track_visibility='onchange'
    )
    express_type = fields.Char(string='承运商')
    express_code = fields.Char(u'快递单号', copy=False)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    qc_result = fields.Binary(u'质检报告',
                              help=u'点击上传质检报告')
    finance_category_id = fields.Many2one(
        'core.category',
        string=u'收发类别',
        ondelete='restrict',
        states={'done': [('readonly', True)]},
        domain=[('type', '=', 'finance')],
        context={'type': 'finance'},
        help=u'生成凭证时从此字段上取商品科目的对方科目',
    )
    all_line_done = fields.Boolean(u'出库行都完成', compute='compute_all_line_done', store=True)

    @api.one
    @api.depends('line_out_ids.state')
    def compute_all_line_done(self):
        """如果所有出库行的状态都为done,则置为True,以便控制发料和出库按钮显隐"""
        if all(line.state == 'done' for line in self.line_out_ids):
            self.all_line_done = True

    def scan_barcode_move_line_operation(self, line, conversion):
        """
        在原移库明细行中更新数量和辅助数量，不创建新行
        :return:
        """
        line.goods_qty += 1
        line.goods_uos_qty = line.goods_qty / conversion
        return True

    def scan_barcode_inventory_line_operation(self, line, conversion):
        '''盘点单明细行数量增加'''
        line.inventory_qty += 1
        line.inventory_uos_qty = line.inventory_qty / conversion
        line.difference_qty += 1
        line.difference_uos_qty = line.difference_qty / conversion

        return True

    def scan_barcode_move_in_out_operation(self, move, att, conversion, goods, val):
        """
        对仓库各种移库单据上扫码的统一处理
        :return: 是否创建新的明细行
        """
        create_line = False
        loop_field = 'line_in_ids' if val['type'] == 'in' else 'line_out_ids'
        for line in move[loop_field]:
            line.cost_unit = (line.goods_id.price if val['type'] in ['out', 'internal']
                              else line.goods_id.cost)  # 其他出入库单 、内部调拨单
            line.price_taxed = (line.goods_id.price if val['type'] == 'out'
                                else line.goods_id.cost)  # 采购或销售单据
            # 如果商品属性或商品上存在条码，且明细行上已经存在该商品，则数量累加
            if (att and line.attribute_id == att) or (goods and line.goods_id == goods):
                create_line = self.scan_barcode_move_line_operation(
                    line, conversion)
        return create_line

    def scan_barcode_inventory_operation(self, move, att, conversion, goods, val):
        '''盘点单扫码操作'''
        create_line = False
        for line in move.line_ids:
            # 如果商品属性上存在条码 或 商品上存在条码
            if (att and line.attribute_id == att) or (goods and line.goods_id == goods):
                create_line = self.scan_barcode_inventory_line_operation(
                    line, conversion)
        return create_line

    def scan_barcode_each_model_operation(self, model_name, order_id, att, goods, conversion):
        val = {}
        create_line = False  # 是否创建新的明细行
        order = self.env[model_name].browse(order_id)
        if model_name in ['wh.out', 'wh.in', 'wh.internal']:
            move = order.move_id
        # 在其他出库单上扫描条码
        if model_name == 'wh.out':
            val['type'] = 'out'
        # 在其他入库单上扫描条码
        if model_name == 'wh.in':
            val['type'] = 'in'
        # 销售出入库单的二维码
        if model_name == 'sell.delivery':
            move = order.sell_move_id
            val['type'] = order.is_return and 'in' or 'out'
        # 采购出入库单的二维码
        if model_name == 'buy.receipt':
            move = order.buy_move_id
            val['type'] = order.is_return and 'out' or 'in'
        # 调拔单的扫描条码
        if model_name == 'wh.internal':
            val['type'] = 'internal'
        if model_name != 'wh.inventory':
            create_line = self.scan_barcode_move_in_out_operation(
                move, att, conversion, goods, val)

        # 盘点单的扫码
        if model_name == 'wh.inventory':
            move = order
            val['type'] = 'out'
            create_line = self.scan_barcode_inventory_operation(
                move, att, conversion, goods, val)

        return move, create_line, val

    @api.multi
    def check_goods_qty(self, goods, attribute, warehouse):
        '''SQL来取指定商品，属性，仓库，的当前剩余数量'''

        if attribute:
            change_conditions = "AND line.attribute_id = %s" % attribute.id
        elif goods:
            change_conditions = "AND line.goods_id = %s" % goods.id
        else:
            change_conditions = "AND 1 = 0"
        self.env.cr.execute('''
                       SELECT sum(line.qty_remaining) as qty
                       FROM wh_move_line line

                       WHERE line.warehouse_dest_id = %s
                             AND line.state = 'done'
                             %s
                   ''' % (warehouse.id, change_conditions,))
        return self.env.cr.fetchone()

    def prepare_move_line_data(self, att, val, goods, move):
        """
        准备移库单明细数据
        :return: 字典
        """
        # 若传入的商品属性 att 上条码存在则取属性对应的商品，否则取传入的商品 goods
        goods = att and att.goods_id or goods
        goods_id = goods.id
        uos_id = goods.uos_id.id
        uom_id = goods.uom_id.id
        tax_rate = goods.tax_rate
        attribute_id = att and att.id or False
        conversion = goods.conversion
        # 采购入库取成本价，销售退货取销售价;采购退货取成本价，销售发货取销售价
        price_taxed = move._name == 'buy.receipt' and goods.cost or goods.price
        cost_unit = val['type'] == 'out' and 0 or goods.cost / \
            (1 + tax_rate * 0.01)

        val.update({
            'goods_id': goods_id,
            'attribute_id': attribute_id,
            'warehouse_id': move.warehouse_id.id,
            'uos_id': uos_id,
            'uom_id': uom_id,
        })
        if move._name != 'wh.inventory':
            val.update({
                'warehouse_dest_id': move.warehouse_dest_id.id,
                'goods_uos_qty': 1.0 / conversion,
                'goods_qty': 1,
                'price_taxed': price_taxed,
                'tax_rate': tax_rate,
                'cost_unit': cost_unit,
                'move_id': move.id})
        else:
            val.update({
                'inventory_uos_qty': 1.0 / conversion,
                'inventory_qty': 1,
                'real_uos_qty': 0,
                'real_qty': 0,
                'difference_uos_qty': 1.0 / conversion,
                'difference_qty': 1,
                'inventory_id': move.id})
        return val

    @api.model
    def check_barcode(self, model_name, order_id, att, goods):
        pass

    @api.model
    def scan_barcode(self, model_name, barcode, order_id):
        """
        扫描条码
        :param model_name: 模型名
        :param barcode: 条码
        :param order_id: 单据id
        :return:
        """
        att = self.env['attribute'].search([('ean', '=', barcode)])
        goods = self.env['goods'].search([('barcode', '=', barcode)])
        line_model = (model_name == 'wh.inventory' and 'wh.inventory.line'
                      or 'wh.move.line')

        if not att and not goods:
            raise UserError(u'条码为  %s 的商品不存在' % (barcode))
        else:
            self.check_barcode(model_name, order_id, att, goods)
            conversion = att and att.goods_id.conversion or goods.conversion
            move, create_line, val = self.scan_barcode_each_model_operation(
                model_name, order_id, att, goods, conversion)
            if not create_line:
                self.env[line_model].create(
                    self.prepare_move_line_data(att, val, goods, move))

    def check_qc_result(self):
        """
        检验质检报告是否上传
        :return:
        """
        qc_rule = self.env['qc.rule'].search([
            ('move_type', '=', self.origin),
            ('warehouse_id', '=', self.warehouse_id.id),
            ('warehouse_dest_id', '=', self.warehouse_dest_id.id)])
        if qc_rule and not self.qc_result:
            raise UserError(u'请先上传质检报告')

    def prev_approve_order(self):
        """
        确认单据之前所做的处理
        :return:
        """
        for order in self:
            if not order.line_out_ids and not order.line_in_ids:
                raise UserError(u'单据的明细行不可以为空')
            order.check_qc_result()

    @api.multi
    def approve_order(self):
        """
        确认单据
        :return:
        """
        for order in self:
            order.prev_approve_order()
            order.line_out_ids.action_done()
            order.line_in_ids.action_done()

        # 每次移库完成，清空库位上商品数量为0的商品和属性（不合逻辑的数据）
        for loc in self.env['location'].search([('save_qty', '=', 0),
                                                ('goods_id', '!=', False)
                                                ]):
            if not loc.current_qty:
                continue    # pragma: no cover
        return self.write({
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })

    def prev_cancel_approved_order(self):
        pass

    @api.multi
    def cancel_approved_order(self):
        """
        撤销确认单据
        :return:
        """
        for order in self:
            order.prev_cancel_approved_order()
            order.line_out_ids.action_draft()
            order.line_in_ids.action_draft()

        return self.write({
            'approve_uid': False,
            'approve_date': False,
        })

    @api.multi
    def write(self, vals):
        """
        作废明细行
        """
        if vals.get('state', False) == 'cancel':
            for order in self:
                order.line_out_ids.action_cancel()
                order.line_in_ids.action_cancel()

        return super(WhMove, self).write(vals)

    @api.multi
    def create_zero_wh_in(self, wh_in, model_name):
        """
        创建一个缺货向导
        :param wh_in: 单据实例
        :param model_name: 单据模型
        :return:
        """
        all_line_message = ""
        today = fields.Datetime.now()
        line_in_ids = []
        goods_list = []
        for line in wh_in.line_out_ids:
            if line.goods_id.no_stock:
                continue
            result = self.check_goods_qty(
                line.goods_id, line.attribute_id, wh_in.warehouse_id)
            result = result[0] or 0
            if line.goods_qty > result and not line.lot_id and not self.env.context.get('wh_in_line_ids'):
                # 在销售出库时如果临时缺货，自动生成一张盘盈入库单
                if (line.goods_id.id, line.attribute_id.id) in goods_list:
                    continue
                goods_list.append((line.goods_id.id, line.attribute_id.id))
                all_line_message += u'商品 %s ' % line.goods_id.name
                if line.attribute_id:
                    all_line_message += u' 型号%s' % line.attribute_id.name
                line_in_ids.append((0, 0, {
                    'goods_id': line.goods_id.id,
                    'attribute_id': line.attribute_id.id,
                    'goods_uos_qty': 0,
                    'uos_id': line.uos_id.id,
                    'goods_qty': 0,
                    'uom_id': line.uom_id.id,
                    'cost_unit': line.goods_id.cost / (1 + line.goods_id.tax_rate * 0.01),
                    'state': 'done',
                    'date': today}))
                all_line_message += u" 当前库存量不足，继续出售请点击确定，并及时盘点库存\n"

            if line.goods_qty <= 0 or line.price_taxed < 0:
                raise UserError(u'商品 %s 的数量和含税单价不能小于0。' % line.goods_id.name)
        if line_in_ids:
            vals = {
                'type': 'inventory',
                'warehouse_id': self.env.ref('warehouse.warehouse_inventory').id,
                'warehouse_dest_id': wh_in.warehouse_id.id,
                'state': 'done',
                'date': today,
                'line_in_ids': line_in_ids}
            return self.env[model_name].open_dialog('goods_inventory', {
                'message': all_line_message,
                'args': [vals],
            })
