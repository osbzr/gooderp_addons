# -*- coding: utf-8 -*-

from openerp import models, fields, api


class goods(models.Model):
    _inherit = 'goods'

    using_batch = fields.Boolean(u'批次管理')
    force_batch_one = fields.Boolean(u'每批次数量为1')
    attribute_ids = fields.One2many('attribute', 'goods_id', string=u'属性')


class attribute(models.Model):
    _name = 'attribute'

    @api.one
    @api.depends('value_ids')
    def _compute_name(self):
        self.name = ' '.join([value.value_id.name for value in self.value_ids])

    name = fields.Char(u'名称', compute='_compute_name', store=True,readonly=True)
    goods_id = fields.Many2one('goods', u'商品')
    value_ids = fields.One2many('attribute.value', 'attribute_id', string=u'属性')


class attribute_value(models.Model):
    _name = 'attribute.value'
    _rec_name = 'value_id'
    attribute_id = fields.Many2one('attribute',u'属性')
    category_id = fields.Many2one('core.category',u'属性',
                                       domain=[('type','=','attribute')],context={'type':'attribute'}
                                       ,required='1')
    value_id = fields.Many2one('attribute.value.value',u'值',
                                       domain="[('category_id','=',category_id)]"
                                       ,required='1')
class attribute_value(models.Model):
    _name = 'attribute.value.value'
    category_id = fields.Many2one('core.category',u'属性',
                                       domain=[('type','=','attribute')],context={'type':'attribute'}
                                       ,required='1')
    name = fields.Char(u'值')
