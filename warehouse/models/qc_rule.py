from odoo import api, fields, models

MOVE_TYPE = [
    ('buy.receipt.buy', '采购入库单'),
    ('buy.receipt.return', '采购退货单'),
    ('sell.delivery.sell', '销售发货单'),
    ('sell.delivery.return', '销售退货单'),
    ('wh.out.others', '其他出库单'),
    ('wh.out.inventory', '盘亏'),
    ('wh.in.others', '其他入库单'),
    ('wh.in.inventory', '盘盈'),
    ('wh.internal', '移库单'),
    ('wh.assembly', '组装单'),
    ('wh.disassembly', '拆卸单'),
    ('outsource', '委外加工单'),
]


class QcRule(models.Model):
    _name = 'qc.rule'
    _description = '质检规则'

    @api.one
    def _compute_warehouse_impl(self):
        '''根据单据类型自动填充上调出仓库'''
        if self.move_type == 'sell.delivery.return':
            self.warehouse_id = self.env.ref('warehouse.warehouse_customer')
        if self.move_type == 'buy.receipt.buy':
            self.warehouse_id = self.env.ref('warehouse.warehouse_supplier')
        if self.move_type == 'wh.in.others':
            self.warehouse_id = self.env.ref('warehouse.warehouse_others')
        if self.move_type == 'wh.in.inventory':
            self.warehouse_id = self.env.ref('warehouse.warehouse_inventory')

    @api.one
    def _compute_warehouse_dest_impl(self):
        '''根据单据类型自动填充上调入仓库'''
        if self.move_type == 'sell.delivery.sell':
            self.warehouse_dest_id = self.env.ref(
                'warehouse.warehouse_customer')
        if self.move_type == 'buy.receipt.return':
            self.warehouse_dest_id = self.env.ref(
                'warehouse.warehouse_supplier')
        if self.move_type == 'wh.out.others':
            self.warehouse_dest_id = self.env.ref('warehouse.warehouse_others')
        if self.move_type == 'wh.out.inventory':
            self.warehouse_dest_id = self.env.ref(
                'warehouse.warehouse_inventory')

    @api.onchange('move_type')
    def onchange_move_type(self):
        '''根据单据类型自动填充上调入仓库或调出仓库'''
        self._compute_warehouse_impl()
        self._compute_warehouse_dest_impl()

    move_type = fields.Selection(MOVE_TYPE,
                                 '单据类型',
                                 required=True,
                                 help='待质检的单据类型')
    warehouse_id = fields.Many2one('warehouse',
                                   '调出仓库',
                                   ondelete='restrict',
                                   help='移库单的来源仓库')
    warehouse_dest_id = fields.Many2one('warehouse',
                                        '调入仓库',
                                        ondelete='restrict',
                                        help='移库单的目的仓库')
