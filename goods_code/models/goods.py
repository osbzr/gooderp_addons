
from odoo import models, fields


class goods(models.Model):
    _inherit = "goods"

    _sql_constraints = [
        ('code_uniq', 'unique(code)', '编号必须唯一'),
    ]