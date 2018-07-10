# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime



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
    credit_time = fields.Float(u'信用天数', track_visibility='onchange',
                                help=u'客户购买商品时，本次结算单的到期日为结算单日期+信用天数')
    active = fields.Boolean(u'启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    tag_ids = fields.Many2many('core.value',
                               ondelete='restrict',
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
    date_qualify = fields.Date(u'资质到期日期')
    days_qualify = fields.Float(u'资质到期天数',
                                compute='compute_days_qualify',
                                store=True,
                                help=u'当天到资质到期日期的天数差',
                                )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '业务伙伴不能重名')
    ]

    @api.constrains('name', 'c_category_id', 's_category_id')
    def _check_category_exists(self):
        # 客户 或 供应商 类别有一个必输
        if self.name and  not self.s_category_id and not self.c_category_id:
            raise UserError(u'请选择类别')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        在many2one字段中支持按编号搜索
        """
        args = args or []
        if name:
            res_id = self.search([('code','=',name)])
            if res_id:
                return res_id.name_get()
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

    @api.multi
    def write(self, vals):
        # 业务伙伴应收/应付余额不为0时，不允许取消对应的客户/供应商身份
        if self.c_category_id and vals.get('c_category_id') == False and self.receivable != 0:
            raise UserError(u'该客户应收余额不为0，不能取消客户类型')
        if self.s_category_id and vals.get('s_category_id') == False and self.payable != 0:
            raise UserError(u'该供应商应付余额不为0，不能取消供应商类型')
        return super(Partner, self).write(vals)

    @api.one
    @api.depends('date_qualify')
    def compute_days_qualify(self):
        """计算当天距离资质到期日期的天数"""
        today = datetime.strptime(fields.Date.context_today(self), '%Y-%m-%d')
        date_qualify = self.date_qualify and datetime.strptime(
            self.date_qualify, '%Y-%m-%d') or today
        day = (date_qualify - today).days
        self.days_qualify = day
