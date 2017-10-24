# -*- coding: utf-8 -*-
# #############################################################################

# #############################################################################
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class FinanceConfigWizard(models.TransientModel):
    _name = 'finance.config.settings'
    _inherit = 'res.config.settings'
    _description = u'会计默认设置'

    # 凭证
    # 凭证日期
    default_voucher_date = fields.Selection([('today', u'当前日期'), ('last', u'上一凭证日期')],
                                            string=u'新凭证的默认日期', default='today', help=u'选择新凭证的默认日期')
    # 凭证号重置设置  此部分参与了步科的设计
    default_auto_reset = fields.Boolean(u'是否重置凭证号', )
    default_reset_period = fields.Selection([('year', u'每年'), ('month', u'每月')], u'重置间隔', required=True,
                                            default='month')
    default_reset_init_number = fields.Integer(
        u'重置后起始数字', required=True, default=1, help=u"重置后，起始编号的数字，例从1起：1，2，3....")

    # 资产负债表 利润表
    # 是否能查看未结账期间
    default_period_domain = fields.Selection([('can', u'能'), ('cannot', u'不能')],
                                             string=u'是否能查看未结账期间', default='can', help=u'是否能查看未结账期间')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def set_default_voucher_date(self):
        voucher_date = self.default_voucher_date
        res = self.env['ir.values'].set_default(
            'finance.config.settings', 'default_voucher_date', voucher_date)
        return res

    @api.multi
    def set_default_period_domain(self):
        period_domain = self.default_period_domain
        res = self.env['ir.values'].set_default(
            'finance.config.settings', 'default_period_domain', period_domain)
        return res

    @api.multi
    def set_default_auto_reset(self):
        auto_reset = self.default_auto_reset
        res = self.env['ir.values'].set_default(
            'finance.config.settings', 'default_auto_reset', auto_reset)
        return res

    @api.multi
    def set_default_reset_period(self):
        reset_period = self.default_reset_period
        res = self.env['ir.values'].set_default(
            'finance.config.settings', 'default_reset_period', reset_period)
        return res

    @api.multi
    def set_default_reset_init_number(self):
        reset_init_number = self.default_reset_init_number
        res = self.env['ir.values'].set_default('finance.config.settings', 'default_reset_init_number',
                                                reset_init_number)
        return res
