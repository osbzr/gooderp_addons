# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp import models, fields, api


class wh_move(models.Model):
    _name = 'wh.move'

    MOVE_STATE = [
        ('draft', u'草稿'),
        ('done', u'已审核'),
    ]
    
    @api.one
    @api.depends('line_out_ids','line_in_ids')
    def _compute_total_qty(self):
        goods_total = 0
        if self.line_in_ids:
            # 入库产品总数
            goods_total = sum(line.goods_qty for line in self.line_in_ids)
        elif self.line_out_ids:
            # 出库产品总数
            goods_total = sum(line.goods_qty for line in self.line_out_ids)
        self.total_qty = goods_total

    @api.model
    def _get_default_warehouse(self):
        '''获取调出仓库'''
        if self.env.context.get('warehouse_type', 'stock'):
            return self.env['warehouse'].get_warehouse_by_type(
                    self.env.context.get('warehouse_type', 'stock'))

    @api.model
    def _get_default_warehouse_dest(self):
        '''获取调入仓库'''
        if self.env.context.get('warehouse_dest_type', 'stock'):
            return self.env['warehouse'].get_warehouse_by_type(
                    self.env.context.get('warehouse_dest_type', 'stock'))

    origin = fields.Char(u'源单类型', required=True,
                         help=u'源单类型')
    name = fields.Char(u'单据编号', copy=False, default='/',
                       help=u'单据编号，创建时会自动生成')
    state = fields.Selection(MOVE_STATE, u'状态', copy=False, default='draft',
                             help=u'移库单状态标识，新建时状态为未审核;审核后状态为已审核')
    partner_id = fields.Many2one('partner', u'业务伙伴', ondelete='restrict',
                                 help=u'该单据对应的业务伙伴')
    date = fields.Date(u'单据日期', required=True, copy=False, default=fields.Date.context_today,
                       help=u'单据创建日期，默认为当前天')
    warehouse_id = fields.Many2one('warehouse', u'调出仓库',
                                   ondelete='restrict',
                                   required=True,
                                   default=_get_default_warehouse,
                                   help=u'移库单的来源仓库')
    warehouse_dest_id = fields.Many2one('warehouse', u'调入仓库',
                                        ondelete='restrict',
                                        required=True,
                                        default=_get_default_warehouse_dest,
                                        help=u'移库单的目的仓库')
    approve_uid = fields.Many2one('res.users', u'审核人',
                                  copy=False, ondelete='restrict',
                                  help=u'移库单的审核人')
    approve_date = fields.Datetime(u'审核日期', copy=False)
    line_out_ids = fields.One2many('wh.move.line', 'move_id', u'出库明细',
                                   domain=[('type', '=', 'out')],
                                   context={'type': 'out'}, copy=True,
                                   help=u'出库类型的移库单对应的出库明细')
    line_in_ids = fields.One2many('wh.move.line', 'move_id', u'入库明细',
                                  domain=[('type', '=', 'in')],
                                  context={'type': 'in'}, copy=True,
                                  help=u'入库类型的移库单对应的入库明细')
    note = fields.Text(u'备注',
                       help=u'可以为该单据添加一些需要的标识信息')
    total_qty = fields.Integer(u'产品总数', compute=_compute_total_qty, store=True,
                               help=u'该移库单的入/出库明细行包含的产品总数')

    @api.model
    def scan_barcode(self,model_name,barcode,order_id):
        val = {}
        create_line = False # 是否需要创建明细行
        att = self.env['attribute'].search([('ean','=',barcode)])
        goods = self.env['goods'].search([('barcode', '=', barcode)])

        if not att and not goods:
            raise osv.except_osv(u'错误', u'ean为  %s 的产品不存在' % (barcode))
        else:
            conversion = att and att.goods_id.conversion or goods.conversion
            if model_name in ['wh.out','wh.in']:
                move = self.env[model_name].browse(order_id).move_id
            # 在其他出库单上扫描条码
            if model_name == 'wh.out':
                val['type'] = 'out'
                for line in move.line_out_ids:
                    line.cost_unit = line.goods_id.price
                    # 如果产品属性上存在条码，且明细行上已经存在该产品，则数量累加
                    if att and line.attribute_id.id == att.id:
                        line.goods_qty += 1
                        line.goods_uos_qty = line.goods_qty / conversion
                        create_line = True
                    # 如果产品上存在条码，且明细行上已经存在该产品，则数量累加
                    elif goods and line.goods_id.id == goods.id:
                        line.goods_qty += 1
                        line.goods_uos_qty = line.goods_qty / conversion
                        create_line = True
            # 在其他入库单上扫描条码
            if model_name == 'wh.in':
                val['type'] = 'in'
                for line in move.line_in_ids:
                    line.cost_unit = line.goods_id.cost
                    # 如果产品属性上存在条码
                    if att and line.attribute_id.id == att.id:
                        line.goods_qty += 1
                        line.goods_uos_qty = line.goods_qty / conversion
                        create_line = True
                    # 如果产品上存在条码
                    elif goods and line.goods_id.id == goods.id:
                        line.goods_qty += 1
                        line.goods_uos_qty = line.goods_qty / conversion
                        create_line = True
            #销售出入库单的二维码
            if model_name == 'sell.delivery':
                move = self.env[model_name].browse(order_id).sell_move_id
                if self.env[model_name].browse(order_id).is_return == True:
                    val['type'] = 'in'
                    for line in move.line_in_ids:
                        line.price_taxed = line.goods_id.cost
                        # 如果产品属性上存在条码
                        if att and line.attribute_id.id == att.id:
                            line.goods_qty += 1
                            line.goods_uos_qty = line.goods_qty / conversion
                            create_line = True
                        # 如果产品上存在条码
                        elif goods and line.goods_id.id == goods.id:
                            line.goods_qty += 1
                            line.goods_uos_qty = line.goods_qty / conversion
                            create_line = True
                else:
                    val['type'] = 'out'
                    for line in move.line_out_ids:
                        line.price_taxed = line.goods_id.price
                        # 如果产品属性上存在条码
                        if att and line.attribute_id.id == att.id:
                            line.goods_qty += 1
                            line.goods_uos_qty = line.goods_qty / conversion
                            create_line = True
                        # 如果产品上存在条码
                        elif goods and line.goods_id.id == goods.id:
                            line.goods_qty += 1
                            line.goods_uos_qty = line.goods_qty / conversion
                            create_line = True
            #采购出入库单的二维码
            if model_name == 'buy.receipt':
                move = self.env[model_name].browse(order_id).buy_move_id
                if self.env[model_name].browse(order_id).is_return == True:
                    val['type'] = 'out'
                    for line in move.line_out_ids:
                        line.price_taxed = line.goods_id.price
                        # 如果产品属性上存在条码
                        if att and line.attribute_id.id == att.id:
                            line.goods_qty += 1
                            line.goods_uos_qty = line.goods_qty / conversion
                            create_line = True
                        # 如果产品上存在条码
                        elif goods and line.goods_id.id == goods.id:
                            line.goods_qty += 1
                            line.goods_uos_qty = line.goods_qty / conversion
                            create_line = True
                else:
                    val['type'] = 'in'
                    for line in move.line_in_ids:
                        line.price_taxed = line.goods_id.cost
                        # 如果产品属性上存在条码
                        if att and line.attribute_id.id == att.id:
                            line.goods_qty += 1
                            line.goods_uos_qty = line.goods_qty / conversion
                            create_line = True
                        # 如果产品上存在条码
                        elif goods and line.goods_id.id == goods.id:
                            line.goods_qty += 1
                            line.goods_uos_qty = line.goods_qty / conversion
                            create_line = True
            if att:
                goods_id = att.goods_id.id
                uos_id = att.goods_id.uos_id.id
                uom_id = att.goods_id.uom_id.id
                attribute_id = att.id
                conversion = att.goods_id.conversion
                if val['type'] == 'in':
                    # 入库操作取产品的成本
                    price = cost_unit = att.goods_id.cost
                elif val['type'] == 'out':
                    # 出库操作取产品的零售价
                    price = cost_unit = att.goods_id.price
            elif goods:
                goods_id = goods.id
                uos_id = goods.uos_id.id
                uom_id = goods.uom_id.id
                attribute_id = False
                conversion = goods.conversion
                if val['type'] == 'in':
                    # 入库操作取产品的成本
                    price = cost_unit = goods.cost
                elif val['type'] == 'out':
                    # 出库操作取产品的零售价
                    price = cost_unit = goods.price
            val.update({
              'goods_id': goods_id,
              'attribute_id': attribute_id,
              'warehouse_id': move.warehouse_id.id,
              'warehouse_dest_id': move.warehouse_dest_id.id,
              'goods_uos_qty': 1.0 / conversion,
              'uos_id': uos_id,
              'goods_qty': 1,
              'uom_id': uom_id,
              'price_taxed': price,
              'cost_unit': cost_unit,
              'move_id': move.id})
            if create_line == False:
                self.env['wh.move.line'].create(val)

    @api.multi
    def unlink(self):
        for move in self:
            if move.state == 'done':
                raise osv.except_osv(u'错误', u'不可以删除已经完成的单据')

        return super(wh_move, self).unlink()

    def prev_approve_order(self):
        for order in self:
            if not order.line_out_ids and not order.line_in_ids:
                raise osv.except_osv(u'错误', u'单据的明细行不可以为空')

    @api.multi
    def approve_order(self):
        for order in self:
            order.prev_approve_order()
            order.line_out_ids.action_done()
            order.line_in_ids.action_done()

        return self.write({
                'approve_uid': self.env.uid,
                'approve_date': fields.Datetime.now(self),
                'state': 'done',
            })

    def prev_cancel_approved_order(self):
        pass

    @api.multi
    def cancel_approved_order(self):
        for order in self:
            order.prev_cancel_approved_order()
            order.line_out_ids.action_cancel()
            order.line_in_ids.action_cancel()

        return self.write({
                'approve_uid': False,
                'approve_date': False,
                'state': 'draft',
            })
