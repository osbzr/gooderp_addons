# -*- coding: utf-8 -*-

from odoo import fields, models
import odoo.addons.decimal_precision as dp


class vendor_goods(models.Model):
    _name = 'vendor.goods'

    goods_id = fields.Many2one(
        string=u'商品',
        required=True,
        comodel_name='goods',
        ondelete='cascade',
        help=u'商品',
    )

    vendor_id = fields.Many2one(
        string=u'供应商',
        required=True,
        comodel_name='partner',
        domain=[('s_category_id','!=',False)],
        ondelete='cascade',
        help=u'供应商',
    )

    price = fields.Float(u'供货价',
                         digits=dp.get_precision('Amount'),
                         help=u'供应商提供的价格')

    code = fields.Char(u'供应商产品编号',
                       help=u'供应商提供的产品编号')

    name = fields.Char(u'供应商产品名称',
                       help=u'供应商提供的产品名称')

    min_qty = fields.Float(u'最低订购量',
                           digits=dp.get_precision('Quantity'),
                           help=u'采购产品时，大于或等于最低订购量时，产品的价格才取该行的供货价')


class partner(models.Model):
    _inherit = 'partner'

    goods_ids = fields.One2many(
        string=u'供应产品',
        comodel_name='vendor.goods',
        inverse_name='vendor_id',
        help=u'供应商供应的产品价格列表',
    )


class goods(models.Model):

    _inherit = 'goods' 

    vendor_ids = fields.One2many(
        string=u'供应价格',
        comodel_name='vendor.goods',
        inverse_name='goods_id',
        help=u'各供应商提供的基于最低订购量的供货价格列表',
    )
