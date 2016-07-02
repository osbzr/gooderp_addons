# -*- encoding: utf-8 -*-
# #############################################################################

# #############################################################################
import logging

from openerp.osv import fields, osv
from openerp import api, fields, models, _

_logger = logging.getLogger(__name__)


class finance_config_wizard(osv.osv_memory):
    _name = 'finance.config.settings'
    _inherit = 'res.config.settings'

    # 凭证
    # 凭证日期
    default_voucher_date = fields.Selection([('today', u'当前日期'), ('last', u'上一凭证日期')],
                                            string=u'新凭证的默认日期', default='today', help=u'选择新凭证的默认日期')

    # 资产负债表 利润表
    # 是否能查看未结账期间
    default_period_domain = fields.Selection([('can', u'能'), ('cannot', u'不能')],
                                         string=u'是否能查看未结账期间', default='can', help=u'是否能查看未结账期间')

    @api.multi
    def set_default_voucher_date(self):
        voucher_date = self.default_voucher_date
        res = self.env['ir.values'].set_default('finance.config.settings', 'default_voucher_date', voucher_date)
        return res

    @api.multi
    def set_default_period_domain(self):
        period_domain = self.default_period_domain
        res = self.env['ir.values'].set_default('finance.config.settings', 'default_period_domain', period_domain)
        return res
