# -*- coding: utf-8 -*-
from odoo.osv import osv
from odoo.report import report_sxw
from odoo import models, fields, api
import math


class ActionReportPickingWrapped(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(ActionReportPickingWrapped, self).__init__(
            cr, uid, name, context=context)
        self.localcontext.update({
            'paginate': self._paginate,
            'rmb_upper': self._rmb_upper,
            'rmb_format': self._rmb_format,
        })
        self.context = context

    def _rmb_upper(self, value):
        env = api.Environment(self.cr, self.uid, self.context)
        return env['res.currency'].rmb_upper(value)

    def _rmb_format(self, value):
        """
                        将数值按位数分开
        """
        if abs(value) < 0.01:
            # 值为0的不输出，即返回12个空格
            return ['' for i in range(12)]
        # 先将数字转为字符，去掉小数点，然后和12个空格拼成列表，取最后12个元素返回
        return (['' for i in range(12)] + list(('%0.2f' % value).replace('.', '')))[-12:]

    def _paginate(self, items, max_per_page=5):
        """
        分页函数
        items 为要分页的条目们
        max_per_page 设定每页条数
        返回：页数
        """
        count = len(items)
        return int(math.ceil(float(count) / max_per_page))


class ReportVoucher(osv.AbstractModel):
    _name = 'report.finance.report_voucher_view'
    _inherit = 'report.abstract_report'
    _template = 'finance.report_voucher_view'
    _wrapped_report_class = ActionReportPickingWrapped
    _description = u'会计凭证打印'
