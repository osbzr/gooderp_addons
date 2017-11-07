# -*- coding: utf-8 -*-
import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, _
from odoo.exceptions import UserError

CORE_COST_METHOD = [('average', u'全月一次加权平均法'),
                    ('std',u'定额成本'),
                    ('fifo', u'先进先出法'),
                    ]


class Goods(models.Model):
    _name = 'goods'
    _description = u'商品'

    @api.model
    def _get_default_not_saleable_impl(self):
        return False

    @api.model
    def _get_default_not_saleable(self):
        return self._get_default_not_saleable_impl()

    @api.multi
    def name_get(self):
        '''在many2one字段里显示 编号_名称'''
        res = []

        for Goods in self:
            res.append((Goods.id, Goods.code and (
                Goods.code + '_' + Goods.name) or Goods.name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        '''在many2one字段中支持按编号搜索'''
        args = args or []
        if name:
            args.append(('code', 'ilike', name))
            goods_ids = self.search(args)
            if goods_ids:
                return goods_ids.name_get()
            else:
                args.remove(('code', 'ilike', name))
        return super(Goods, self).name_search(name=name, args=args,
                                              operator=operator, limit=limit)

    @api.model
    def create(self, vals):
        '''导入商品时，如果辅助单位为空，则用计量单位来填充它'''
        if not vals.get('uos_id'):
            vals.update({'uos_id': vals.get('uom_id')})
        return super(Goods, self).create(vals)

    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.has_key('name'):
            default.update(name=_('%s (copy)') % (self.name))
        return super(Goods, self).copy(default=default)

    code = fields.Char(u'编号')
    name = fields.Char(u'名称', required=True, copy=False)
    category_id = fields.Many2one('core.category', u'核算类别',
                                  ondelete='restrict',
                                  domain=[('type', '=', 'goods')],
                                  context={'type': 'goods'}, required=True,
                                  help=u'从会计科目角度划分的类别',
                                  )
    uom_id = fields.Many2one('uom', ondelete='restrict',
                             string=u'计量单位', required=True)
    uos_id = fields.Many2one('uom', ondelete='restrict', string=u'辅助单位')
    conversion = fields.Float(
        string=u'转化率', default=1, digits=(16, 3),
        help=u'1个辅助单位等于多少计量单位的数量，如1箱30个苹果，这里就输入30')
    cost = fields.Float(u'成本',
                        digits=dp.get_precision('Amount'))
    cost_method = fields.Selection(CORE_COST_METHOD, u'存货计价方法',
                                   help=u'''GoodERP仓库模块使用先进先出规则匹配
                                   每次出库对应的入库成本和数量，但不实时记账。
                                   财务月结时使用此方法相应调整发出成本''')
    tax_rate = fields.Float(u'税率(%)',
                            help=u'商品税率')
    not_saleable = fields.Boolean(u'不可销售',
                                  default=_get_default_not_saleable,
                                  help=u'商品是否不可销售，勾选了就不可销售，未勾选可销售')
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    brand = fields.Many2one('core.value', u'品牌',
                            ondelete='restrict',
                            domain=[('type', '=', 'brand')],
                            context={'type': 'brand'})

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '商品不能重名'),
        ('conversion_no_zero', 'check(conversion != 0)', '商品的转化率不能为0')
    ]
