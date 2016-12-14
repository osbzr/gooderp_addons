# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
from odoo.exceptions import UserError


class partner(models.Model):
    '''
    业务伙伴可能是客户： c_category_id 非空

    '''
    _name = 'partner'
    _inherit = ['mail.thread']
    code = fields.Char(u'编号')
    name = fields.Char(u'名称', required=True,)
    main_mobile = fields.Char(u'主要手机号', required=True,)
    c_category_id = fields.Many2one('core.category', u'客户类别',
                                    ondelete='restrict',
                                    domain=[('type', '=', 'customer')],
                                    context={'type': 'customer'})
    s_category_id = fields.Many2one('core.category', u'供应商类别',
                                    ondelete='restrict',
                                    domain=[('type', '=', 'supplier')],
                                    context={'type': 'supplier'})
    receivable = fields.Float(u'应收余额', readonly=True,
                              digits=dp.get_precision('Amount'))
    payable = fields.Float(u'应付余额', readonly=True,
                           digits=dp.get_precision('Amount'))
    tax_num = fields.Char(u'税务登记号')
    bank_name = fields.Char(u'开户行')
    bank_num = fields.Char(u'银行账号')

    credit_limit = fields.Float(u'信用额度', track_visibility='onchange',
                                help=u'客户购买产品时，本次发货金额+客户应收余额要小于客户信用额度')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '业务伙伴不能重名')
    ]