# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp import models
from openerp import fields
from openerp import api


class warehouse(models.Model):
    _inherit = 'warehouse'

    WAREHOUSE_TYPE = [
        ('stock', u'库存'),
        ('supplier', u'供应商'),
        ('customer', u'客户'),
        ('inventory', u'盘点'),
        ('production', u'生产'),
        ('others', u'其他'),
    ]

    name = fields.Char(u'仓库名称')
    code = fields.Char(u'仓库编号')
    type = fields.Selection(WAREHOUSE_TYPE, '类型', default='stock')
    active = fields.Boolean(u'有效', default=True)

    # 使用SQL来取得指定仓库情况下的库存数量
    def get_stock_qty(self):
        for warehouse in self:
            self.env.cr.execute('''
                SELECT sum(line.qty_remaining) as qty,
                       sum(line.qty_remaining * (line.cost / line.goods_qty)) as cost,
                       goods.name as goods
                FROM wh_move_line line
                LEFT JOIN warehouse wh ON line.warehouse_dest_id = wh.id
                LEFT JOIN goods goods ON line.goods_id = goods.id

                WHERE line.qty_remaining > 0
                  AND wh.type = 'stock'
                  AND line.state = 'done'
                  AND line.warehouse_dest_id = %s

                GROUP BY wh.name, goods.name
            ''' % (warehouse.id, ))

            return self.env.cr.dictfetchall()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        # 让warehouse支持使用code来搜索
        if name and not filter(lambda _type: _type[0] == 'code', args):
            warehouses = self.search([('type', '=', 'stock'), ('code', 'ilike', name)])
            if warehouses:
                return warehouses.name_get()

        if not filter(lambda _type: _type[0] == 'type', args):
            args = [['type', '=', 'stock']] + args

        return super(warehouse, self).name_search(name=name, args=args,
            operator=operator, limit=limit)

    @api.multi
    def name_get(self):
        res = []
        for warehouse in self:
            res.append((warehouse.id, u'[%s]%s' % (warehouse.code, warehouse.name)))

        return res

    def get_warehouse_by_type(self, _type):
        if not _type or _type not in map(lambda _type: _type[0], self.WAREHOUSE_TYPE):
            raise osv.except_osv(u'错误', u'仓库类型"%s"不在预先定义的type之中，请联系管理员' % _type)

        warehouses = self.search([('type', '=', _type)], limit=1, order='id asc')
        if not warehouses:
            raise osv.except_osv(u'错误', u'不存在该类型"%s"的仓库，请检查基础数据是否全部导入')

        return warehouses[0]
