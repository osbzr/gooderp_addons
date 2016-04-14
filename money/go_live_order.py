# -*- coding: utf-8 -*-

from openerp import fields, models, api


class go_live_order(models.Model):
    _name = 'go.live.order'
    _description = u'期初余额表'

    @api.model
    def create(self, values):
        new_id = super(go_live_order, self).create(values)
        if values.get('bank_id'):
            bank = self.env['bank.account'].search(
                        [('id', '=', values.get('bank_id'))])
            bank.balance += values.get('balance')
        if values.get('partner_id'):
            partner = self.env['partner'].search(
                        [('id', '=', values.get('partner_id'))])
            partner.receivable += (values.get('receivable') or 0.0)
            partner.payable += (values.get('payable') or 0.0)

        return new_id

    @api.model
    def _get_company_start_date(self):
        return self.env.user.company_id.start_date

    partner_id = fields.Many2one('partner', string=u'业务伙伴')
    bank_id = fields.Many2one('bank.account', string=u'账户')
    name = fields.Char(string=u'编号', copy=False, readonly=True, default='/')
    date = fields.Date(string=u'日期', default=_get_company_start_date,
                                      readonly=True, required=True)
    receivable = fields.Float(u'应收余额')
    payable = fields.Float(u'应付余额')
    balance = fields.Float(u'期初余额')

    _sql_constraints = [
        ('partner_uniq', 'unique(partner_id)', u'业务伙伴必须唯一!'),
        ('bank_uniq', 'unique(bank_id)', u'账户必须唯一!'),
    ]
