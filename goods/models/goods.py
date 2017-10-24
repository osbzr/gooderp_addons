# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Goods(models.Model):
    """
    继承了core里面定义的goods 模块，并定义了视图和添加字段。
    """
    _inherit = 'goods'

    no_stock = fields.Boolean(u'虚拟商品')
    using_batch = fields.Boolean(u'管理批号')
    force_batch_one = fields.Boolean(u'管理序列号')
    attribute_ids = fields.One2many('attribute', 'goods_id', string=u'属性')
    image = fields.Binary(u'图片', attachment=True)
    supplier_id = fields.Many2one('partner',
                                  u'供应商',
                                  ondelete='restrict',
                                  domain=[('s_category_id', '!=', False)])
    price = fields.Float(u'零售价')
    barcode = fields.Char(u'条形码')
    note = fields.Text(u'备注')
    goods_class_id = fields.Many2one(
        'goods.class', string=u'商品分类',
        help="Those categories are used to group similar products for point of sale.")

    _sql_constraints = [
        ('barcode_uniq', 'unique(barcode)', u'条形码不能重复'),
    ]

    @api.onchange('uom_id')
    def onchange_uom(self):
        """
        :return: 当选取单位时辅助单位默认和 单位相等。
        """
        self.uos_id = self.uom_id

    @api.onchange('using_batch')
    def onchange_using_batch(self):
        """
        :return: 当将管理批号的勾去掉后，自动将管理序列号的勾去掉
        """
        if not self.using_batch:
            self.force_batch_one = False

    def conversion_unit(self, qty):
        """ 数量 × 转化率 = 辅助数量
        :param qty: 传进来数量计算出辅助数量
        :return: 返回辅助数量
        """
        self.ensure_one()
        return self.conversion * qty

    def anti_conversion_unit(self, qty):
        """ 数量 = 辅助数量 / 转化率
        :param qty: 传入值为辅助数量
        :return: 数量
        """
        self.ensure_one()
        return self.conversion and qty / self.conversion or 0


class Attribute(models.Model):
    _name = 'attribute'
    _description = u'属性'

    @api.one
    @api.depends('value_ids')
    def _compute_name(self):
        self.name = ' '.join(
            [value.category_id.name + ':' + value.value_id.name for value in self.value_ids])

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        '''在many2one字段中支持按条形码搜索'''
        args = args or []
        if name:
            attribute_ids = self.search([('ean', '=', name)])
            if attribute_ids:
                return attribute_ids.name_get()
        return super(Attribute, self).name_search(
            name=name, args=args, operator=operator, limit=limit)

    ean = fields.Char(u'条码')
    name = fields.Char(u'属性', compute='_compute_name',
                       store=True, readonly=True)
    goods_id = fields.Many2one('goods', u'商品', ondelete='cascade')
    value_ids = fields.One2many(
        'attribute.value', 'attribute_id', string=u'属性')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    _sql_constraints = [
        ('ean_uniq', 'unique (ean)', u'该条码已存在'),
    ]


class AttributeValue(models.Model):
    _name = 'attribute.value'
    _rec_name = 'value_id'
    _description = u'属性明细'

    attribute_id = fields.Many2one('attribute', u'属性', ondelete='cascade')
    category_id = fields.Many2one('core.category', u'属性',
                                  ondelete='cascade',
                                  domain=[('type', '=', 'attribute')],
                                  context={'type': 'attribute'},
                                  required='1')
    value_id = fields.Many2one('attribute.value.value', u'值',
                               ondelete='restrict',
                               domain="[('category_id','=',category_id)]",
                               default=lambda self: self.env.context.get(
                                   'default_category_id'),
                               required='1')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())


class AttributeValueValue(models.Model):
    _name = 'attribute.value.value'
    _description = u'属性值'

    category_id = fields.Many2one('core.category', u'属性',
                                  ondelete='cascade',
                                  domain=[('type', '=', 'attribute')],
                                  context={'type': 'attribute'},
                                  required='1')
    name = fields.Char(u'值')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
