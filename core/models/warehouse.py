# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class Warehouse(models.Model):
    _name = 'warehouse'
    _description = u'仓库'

    # 用户只能创建stock类型的仓库
    WAREHOUSE_TYPE = [
        ('stock', u'库存'),
        ('supplier', u'供应商'),
        ('customer', u'客户'),
        ('inventory', u'盘点'),
        ('production', u'生产'),
        ('others', u'其他'),
    ]

    name = fields.Char(u'名称', required=True)
    code = fields.Char(u'编号')
    type = fields.Selection(WAREHOUSE_TYPE, u'类型', default='stock')
    active = fields.Boolean(u'启用', default=True)
    user_ids = fields.Many2many('res.users', string=u'库管')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '仓库不能重名')
    ]

    @api.multi
    def get_stock_qty(self):
        '''使用SQL来取得指定仓库的库存数量，未考虑属性和批次'''
        for Warehouse in self:
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

                GROUP BY goods.name
            ''' % (Warehouse.id, ))

            return self.env.cr.dictfetchall()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        ''' 让warehouse支持使用code来搜索'''
        args = args or []
        # 将name当成code搜
        if name and not filter(lambda _type: _type[0] == 'code', args):
            warehouses = self.search(
                [('type', '=', 'stock'), ('code', 'ilike', name)])
            if warehouses:
                return warehouses.name_get()
        # 下拉列表只显示stock类型的仓库
        if not filter(lambda _type: _type[0] == 'type', args):
            args = [['type', '=', 'stock']] + args

        return super(Warehouse, self).name_search(name=name, args=args,
                                                  operator=operator, limit=limit)

    @api.multi
    def name_get(self):
        '''将仓库显示为 [编号]名字 的形式'''
        res = []
        for Warehouse in self:
            res.append((Warehouse.id, u'[%s]%s' %
                        (Warehouse.code, Warehouse.name)))

        return res

    def get_warehouse_by_type(self, _type):
        '''返回指定类型的第一个仓库'''
        if not _type or _type not in map(lambda _type: _type[0], self.WAREHOUSE_TYPE):
            raise UserError(u'仓库类型" % s"不在预先定义的type之中，请联系管理员' % _type)

        domain = [('type', '=', _type)]
        # 仓库管理员带出有权限的仓库作为默认值
        if _type == 'stock' and self.env.user.has_group('warehouse.group_warehouse'):
            domain += ['|', ('user_ids', '=', False),
                       ('user_ids', 'in', self._uid)]

        warehouses = self.search(domain, limit=1, order='id asc')
        if not warehouses:
            raise UserError(u'不存在类型为%s的仓库，请检查基础数据是否全部导入' % _type)

        return warehouses[0]
