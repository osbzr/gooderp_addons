# -*- coding: utf-8 -*-
from odoo import models, fields, api


class VoucherTemplate(models.Model):
    _name = 'voucher.template'
    _description = u'凭证模板'

    name = fields.Char(u'模板名称', required=True)
    line_ids = fields.One2many(
        'voucher.template.line', 'template_id', string='模板行')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())


class VoucherTemplateLine(models.Model):
    _name = 'voucher.template.line'
    _description = u'凭证模板明细'

    name = fields.Char(u'摘要')
    account_id = fields.Many2one('finance.account', u'会计科目')
    partner_id = fields.Many2one('partner', u'往来单位')
    goods_id = fields.Many2one('goods', u'商品')
    template_id = fields.Many2one('voucher.template', string='模板id')
    auxiliary_id = fields.Many2one(
        'auxiliary.financing', u'辅助核算', help='辅助核算是对账务处理的一种补充,即实现更广泛的账务处理,\
        以适应企业管理和决策的需要.辅助核算一般通过核算项目来实现', ondelete='restrict')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    
    @api.multi
    @api.onchange('account_id')
    def onchange_account_id(self):
        self.currency_id = self.account_id.currency_id
        self.rate_silent = self.account_id.currency_id.rate
        res = {
            'domain': {
                'partner_id': [('name', '=', False)],
                'goods_id': [('name', '=', False)],
                'auxiliary_id': [('name', '=', False)]}}
        if not self.account_id or not self.account_id.auxiliary_financing:
            return res
        if self.account_id.auxiliary_financing == 'customer':
            res['domain']['partner_id'] = [('c_category_id', '!=', False)]
        elif self.account_id.auxiliary_financing == 'supplier':
            res['domain']['partner_id'] = [('s_category_id', '!=', False)]
        elif self.account_id.auxiliary_financing == 'goods':
            res['domain']['goods_id'] = []
        else:
            res['domain']['auxiliary_id'] = [
                ('type', '=', self.account_id.auxiliary_financing)]
        return res


class VoucherTemplateWizard(models.TransientModel):
    _name = 'voucher.template.wizard'
    _description = u'凭证模板生成向导'

    name = fields.Char(string=u'模板名称')
    is_change_old_template = fields.Boolean(u'修改原有模板')
    old_template_id = fields.Many2one('voucher.template', string=u'旧模板')
    voucher_id = fields.Many2one(
        'voucher', u'凭证id', default=lambda self: self.env.context.get('active_id'))
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def save_as_template(self):
        template_obj = self.env['voucher.template']
        template_line_lsit_dict = [[0, False, {'name': voucher_line.name, 'account_id': voucher_line.account_id.id,
                                               'partner_id': voucher_line.partner_id.id,
                                               'goods_id': voucher_line.goods_id.id,
                                               'auxiliary_id': voucher_line.auxiliary_id.id}] for voucher_line in
                                   self.voucher_id.line_ids]
        if self.is_change_old_template:
            self.old_template_id.line_ids = False
            self.old_template_id.write({'line_ids': template_line_lsit_dict})
        else:
            template_obj.create(
                {'name': self.name, 'line_ids': template_line_lsit_dict})


class Voucher(models.Model):
    _inherit = 'voucher'
    template_id = fields.Many2one('voucher.template', string='模板')

    @api.onchange('template_id')
    def onchange_template_id(self):
        template_line_lsit_dict = [{'name': line.name, 'account_id': line.account_id.id, 'partner_id': line.partner_id.id,
                                    'auxiliary_id': line.auxiliary_id.id, 'goods_id': line.goods_id.id} for line in self.template_id.line_ids]
        self.line_ids = False
        self.line_ids = template_line_lsit_dict
