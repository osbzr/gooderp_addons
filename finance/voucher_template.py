# -*- coding: utf-8 -*-
from odoo import models, fields, api

class VoucherTemplate(models.Model):
    _name = 'voucher.template'
    name = fields.Char(u'模板名称')
    line_ids = fields.One2many('voucher.template.line', 'template_id', string='模板行')


class VoucherTemplateLine(models.Model):
    _name = 'voucher.template.line'
    name = fields.Char(u'摘要')
    account_id = fields.Many2one('finance.account', u'会计科目')
    partner_id = fields.Many2one('partner', u'往来单位')
    goods_id = fields.Many2one('goods', u'商品')
    template_id = fields.Many2one('voucher.template', string='模板id')


class voucher_template_wizard(models.TransientModel):
    _name = 'voucher.template.wizard'

    name = fields.Char(string=u'模板名称')
    is_change_old_template = fields.Boolean(u'修改原有模板')
    old_template_id = fields.Many2one('voucher.template', string=u'旧模板')
    voucher_id = fields.Many2one('voucher', u'凭证id', default=lambda self: self.env.context.get('active_id'))

    @api.multi
    def save_as_template(self):
        template_obj = self.env['voucher.template']
        template_line_lsit_dict = [[0, False, {'name': voucher_line.name, 'account_id': voucher_line.account_id.id, \
                                               'partner_id': voucher_line.partner_id.id, \
                                               'goods_id': voucher_line.goods_id.id}] for voucher_line in
                                   self.voucher_id.line_ids]
        if self.is_change_old_template:
            self.old_template_id.line_ids = False
            self.old_template_id.write({'line_ids': template_line_lsit_dict})
        else:
            template_obj.create({'name': self.name, 'line_ids': template_line_lsit_dict})

class Voucher(models.Model):
    _inherit = 'voucher'
    template_id = fields.Many2one('voucher.template',string='模板')

    @api.onchange('template_id')
    def onchange_template_id(self):
        template_line_lsit_dict = [{'name': line.name, 'account_id': line.account_id.id,'partner_id': line.partner_id.id,
                                               'goods_id': line.goods_id.id} for line in self.template_id.line_ids]
        self.line_ids = False
        self.line_ids =template_line_lsit_dict