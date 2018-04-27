# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools
from odoo.exceptions import UserError
import os
from odoo.tools import misc
import re
# 成本计算方法，已实现 先入先出

CORE_COST_METHOD = [('average', u'全月一次加权平均法'),
                    ('std',u'定额成本'),
                    ('fifo', u'先进先出法'),
                    ]


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.one
    @api.constrains('email')
    def _check_email(self):
        ''' 验证 email 合法性 '''
        if self.email:
            res = re.match('^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', self.email)
            if not res:
                raise UserError(u'请检查邮箱格式是否正确: %s' % self.email)

    start_date = fields.Date(u'启用日期',
                             required=True,
                             default=lambda self: fields.Date.context_today(self))
    cost_method = fields.Selection(CORE_COST_METHOD, u'存货计价方法',
                                   help=u'''GoodERP仓库模块使用先进先出规则匹配
                                   每次出库对应的入库成本和数量，但不实时记账。
                                   财务月结时使用此方法相应调整发出成本''', default='average', required=True)
    draft_invoice = fields.Boolean(u'根据发票确认应收应付',
                                   help=u'勾选这里，所有新建的结算单不会自动记账')
    import_tax_rate = fields.Float(string=u"默认进项税税率")
    output_tax_rate = fields.Float(string=u"默认销项税税率")
    bank_account_id = fields.Many2one('bank.account', string=u'开户行')

    def _get_logo(self):
        return self._get_logo_impl()

    def _get_logo_impl(self):
        ''' 默认取 core/static/description 下的 logo.png 作为 logo'''
        return open(misc.file_open('core/static/description/logo.png').name, 'rb') .read().encode('base64')

    logo = fields.Binary(related='partner_id.image',
                         default=_get_logo, attachment=True)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
