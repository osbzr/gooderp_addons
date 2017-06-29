# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class PosCategory(models.Model):
    _name = "pos.category"
    _description = u"POS产品分类"
    _order = "sequence, name"

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValueError(_('错误 ! 您不能创建循环分类'))

    name = fields.Char(required=True, translate=True, string='名字')
    parent_id = fields.Many2one('pos.category', string='上级分类', index=True)
    child_id = fields.One2many('pos.category', 'parent_id', string='子分类')
    sequence = fields.Integer(u'顺序')
    image = fields.Binary(attachment=True)
    image_medium = fields.Binary(string="Medium-sized image", attachment=True)
    image_small = fields.Binary(string="Small-sized image", attachment=True)
