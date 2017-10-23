# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
from odoo.exceptions import UserError


class Partner(models.Model):
    '''
    业务伙伴可能是客户： c_category_id 非空

    '''
    _name = 'partner'
    _description = u'业务伙伴'
    _inherit = ['mail.thread']

    code = fields.Char(u'编号')
    name = fields.Char(u'名称', required=True,)
    main_mobile = fields.Char(u'主要手机号', required=True,)
    main_address = fields.Char(u'办公地址')
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
    tax_rate = fields.Float(u'税率(%)',
                            help=u'业务伙伴税率')
    bank_name = fields.Char(u'开户行')
    bank_num = fields.Char(u'银行账号')

    credit_limit = fields.Float(u'信用额度', track_visibility='onchange',
                                help=u'客户购买商品时，本次发货金额+客户应收余额要小于客户信用额度')
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    tag_ids = fields.Many2many('core.value',
                               string=u'标签',
                               domain=[('type', '=', 'partner_tag')],
                               context={'type': 'partner_tag'})
    source = fields.Char(u'来源')
    note = fields.Text(u'备注')
    main_contact = fields.Char(u'主联系人')
    responsible_id = fields.Many2one('res.users',
                                     u'负责人员')
    share_id = fields.Many2one('res.users',
                               u'共享人员')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '业务伙伴不能重名')
    ]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        在many2one字段中支持按编号搜索
        """
        args = args or []
        if name:
            args.append(('code', 'ilike', name))
            partners = self.search(args)
            if partners:
                return partners.name_get()
            else:
                args.remove(('code', 'ilike', name))
        return super(Partner, self).name_search(name=name,
                                                args=args,
                                                operator=operator,
                                                limit=limit)
