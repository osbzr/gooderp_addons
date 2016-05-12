# -*- coding: utf-8 -*-

from openerp import models, fields, api


class goods(models.Model):
    _inherit = 'goods'

    using_batch = fields.Boolean(u'批号管理')
    force_batch_one = fields.Boolean(u'每批号数量为1')
    attribute_ids = fields.One2many('attribute', 'goods_id', string=u'属性')
    image=fields.Binary(u'图片')
    supplier_id = fields.Many2one('partner',u'供应商',domain="[('s_category_id','!=',False)]")
    price = fields.Float(u'零售价')

    @api.one
    @api.onchange('uom_id')
    def onchange_uom(self):
        self.uos_id = self.uom_id

    def conversion_unit(self, qty):
        self.ensure_one()
        return self.conversion * qty

    def anti_conversion_unit(self, qty):
        self.ensure_one()
        return self.conversion and qty / self.conversion or 0


class attribute(models.Model):
    _name = 'attribute'

    @api.one
    @api.depends('value_ids')
    def _compute_name(self):
        self.name = ' '.join([value.category_id.name + ':' + value.value_id.name for value in self.value_ids])

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        '''在many2one字段中支持按条形码搜索'''
        args = args or []
        if name:
            goods_ids = self.search([('ean', 'ilike', name)])
            if goods_ids:
                return goods_ids.name_get()
        return super(attribute, self).name_search(
                name=name, args=args, operator=operator, limit=limit)

    ean = fields.Char(u'条码')
    name = fields.Char(u'属性', compute='_compute_name', store=True, readonly=True)
    goods_id = fields.Many2one('goods', u'商品', ondelete='cascade')
    value_ids = fields.One2many('attribute.value', 'attribute_id', string=u'属性')

    _sql_constraints = [
        ('ean_uniq', 'unique (ean)', u'该条码已存在'),
    ]

class attribute_value(models.Model):
    _name = 'attribute.value'
    _rec_name = 'value_id'
    attribute_id = fields.Many2one('attribute', u'属性', ondelete='cascade')
    category_id = fields.Many2one('core.category', u'属性',
                                  ondelete='cascade',
                                  domain=[('type', '=', 'attribute')],
                                  context={'type':'attribute'},
                                  required='1')
    value_id = fields.Many2one('attribute.value.value', u'值',
                                ondelete='restrict', 
                                domain="[('category_id','=',category_id)]",
                                required='1')

class attribute_value_value(models.Model):
    _name = 'attribute.value.value'
    category_id = fields.Many2one('core.category', u'属性',
                                  ondelete='cascade',
                                  domain=[('type', '=', 'attribute')],
                                  context={'type':'attribute'},
                                  required='1')
    name = fields.Char(u'值')
