# -*- coding: utf-8 -*-
from odoo import models, fields


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection([
        ('tree', 'Tree'),
        ('form', 'Form'),
        ('graph', 'Graph'),
        ('pivot', 'Pivot'),
        ('calendar', 'Calendar'),
        ('diagram', 'Diagram'),
        ('gantt', 'Gantt'),
        ('kanban', 'Kanban'),
        ('sales_team_dashboard', 'Sales Team Dashboard'),
        ('search', 'Search'),
        ('qweb', 'QWeb'),
        ('extra_view', 'extra_view')], string=u'视图类型')
