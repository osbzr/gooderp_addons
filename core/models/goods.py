# -*- coding: utf-8 -*-
import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
from odoo.exceptions import UserError


class goods(models.Model):
    _name = 'goods'

    @api.multi
    def name_get(self):
        '''在many2one字段里显示 编号_名称'''
        res = []

        for goods in self:
            res.append((goods.id, goods.code and (
                goods.code + '_' + goods.name) or goods.name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        '''在many2one字段中支持按编号搜索'''
        args = args or []
        if name:
            goods_ids = self.search([('code', 'ilike', name)])
            if goods_ids:
                return goods_ids.name_get()
        return super(goods, self).name_search(name=name, args=args,
                                              operator=operator, limit=limit)

    @api.model
    def create(self, vals):
        '''导入产品时，如果辅助单位为空，则用计量单位来填充它'''
        if not vals.get('uos_id'):
            vals.update({'uos_id': vals.get('uom_id')})
        return super(goods, self).create(vals)

    code = fields.Char(u'编号')
    name = fields.Char(u'名称', required=True)
    category_id = fields.Many2one('core.category', u'产品类别',
                                  ondelete='restrict',
                                  domain=[('type', '=', 'goods')],
                                  context={'type': 'goods'}, required=True)
    uom_id = fields.Many2one('uom', ondelete='restrict',
                             string=u'计量单位', required=True)
    uos_id = fields.Many2one('uom', ondelete='restrict', string=u'辅助单位')
    conversion = fields.Float(
        string=u'转化率', default=1, digits=(16, 3), 
        help=u'1个辅助单位等于多少计量单位的数量，如1箱30个苹果，这里就输入30')
    cost = fields.Float(u'成本',
                        required=True,
                        digits=dp.get_precision('Amount'))

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '产品不能重名')
    ]
