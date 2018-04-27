# -*- coding: utf-8 -*-
# Copyright 2018 上海开阖软件 ((http:www.osbzr.com).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class goods(models.Model):
    _inherit = "goods"

    _sql_constraints = [
        ('code_uniq', 'unique(code)', u'编号必须唯一'),
    ]