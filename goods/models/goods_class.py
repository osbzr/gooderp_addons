# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class GoodsClass(models.Model):
    _name = "goods.class"
    _description = "商品分类"
    _order = "sequence, name"

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValueError('错误 ! 您不能创建循环分类')

    name = fields.Char(required=True, string='名字')
    parent_id = fields.Many2one('goods.class', string='上级分类', index=True)
    child_id = fields.One2many('goods.class', 'parent_id', string='子分类')
    sequence = fields.Integer('顺序')
    type = fields.Selection([('view', '节点'),
                             ('normal', '常规')],
                            '类型',
                            required=True,
                            default='normal',
                            help='货品分类的类型，分为节点和常规，只有节点的分类才可以建下级货品分类，常规分类不可作为上级货品分类')
    note = fields.Text('备注')
    image = fields.Binary(attachment=True)
    image_medium = fields.Binary(string="Medium-sized image", attachment=True)
    image_small = fields.Binary(string="Small-sized image", attachment=True)
    tax_rate = fields.Float('税率(%)',  help='商品分类上的税率')
