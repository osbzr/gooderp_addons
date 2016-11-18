# -*- coding: utf-8 -*-
from odoo import api, fields, models


class res_company(models.Model):
    '''继承公司对象,添加字段'''
    _inherit = 'res.company'
    @api.model
    def _get_operating_cost_account_id(self):
        return self.env.ref('finance.small_business_chart2211001')


    operating_cost_account_id = fields.Many2one('finance.account', default=_get_operating_cost_account_id,
                                                ondelete='restrict',
                                                string='生产费用科目', help='用在组装拆卸的费用上!')