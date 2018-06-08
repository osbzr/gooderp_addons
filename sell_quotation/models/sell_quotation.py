# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

# 销货订单确认状态可选值
SELL_QUOTATION_STATES = [
    ('draft', u'草稿'),
    ('done', u'已确认'),
    ('cancel', u'已作废')]

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
}


class SellQuotation(models.Model):
    _name = 'sell.quotation'
    _inherit = ['mail.thread']
    _description = u'报价单'

    name = fields.Char(u'报价单编号',
                       index=True,
                       copy=False,
                       default='/')
    partner_id = fields.Many2one('partner',
                                 string=u'客户',
                                 required=True,
                                 ondelete='restrict',
                                 states = READONLY_STATES)
    partner_address_id = fields.Many2one('partner.address',
                                         ondelete='restrict',
                                         string=u'联系地址',
                                         states=READONLY_STATES)
    contact = fields.Char(u'联系人',
                          states=READONLY_STATES)
    mobile = fields.Char(u'电话',
                         states=READONLY_STATES)
    user_id = fields.Many2one('res.users',
                              ondelete='restrict',
                              string=u'销售员',
                              default=lambda self: self.env.user,
                              states=READONLY_STATES,
                              required=True)
    date = fields.Date(u'报价日期',
                       states=READONLY_STATES,
                       required=True,
                       default=lambda self: fields.Date.context_today(self))
    opportunity_id = fields.Many2one('opportunity',
                                     ondelete='restrict',
                                     string=u'商机',
                                     states=READONLY_STATES)
    validate_to = fields.Char(u'报价有效期',
                              states=READONLY_STATES,
                              default=u'此报价自即日生效，如有新报价，老报价自动失效')
    line_ids = fields.One2many('sell.quotation.line',
                               'quotation_id',
                               string=u'明细行',
                               states=READONLY_STATES)
    state = fields.Selection(SELL_QUOTATION_STATES,
                             string=u'确认状态',
                             readonly=True,
                             index=True,
                             copy=False,
                             default='draft')
    note = fields.Text(u'备注')

    @api.onchange('partner_address_id')
    def onchange_partner_address_id(self):
        ''' 选择联系人，填充电话 '''
        if self.partner_address_id:
            self.contact = self.partner_address_id.contact
            self.mobile = self.partner_address_id.mobile

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        ''' 选择客户带出其默认联系地址、联系人、电话信息 '''
        if self.partner_id:
            self.contact = self.partner_id.contact
            self.mobile = self.partner_id.mobile

            for child in self.partner_id.child_ids:
                if child.is_default_add:
                    self.partner_address_id = child.id
            if self.partner_id.child_ids and not any([child.is_default_add for child in self.partner_id.child_ids]):
                partners_add = self.env['partner.address'].search(
                    [('partner_id', '=', self.partner_id.id)], order='id')
                self.partner_address_id = partners_add[0].id

            address_list = [
                child_list.id for child_list in self.partner_id.child_ids]
            if address_list:
                return {'domain': {'partner_address_id': [('id', 'in', address_list)]}}
            else:
                self.partner_address_id = False

    @api.multi
    def sell_quotation_done(self):
        ''' 确认报价单 '''
        for quotation in self:
            if quotation.state == 'done':
                raise UserError(u'请不要重复确认！')
            if not quotation.line_ids:
                raise UserError(u'请输入明细行！')

            quotation.state = 'done'

    @api.multi
    def sell_quotation_draft(self):
        ''' 撤销确认报价单 '''
        for quotation in self:
            if quotation.state == 'draft':
                raise UserError(u'请不要重复撤销确认！')

            quotation.state = 'draft'


class SellQuotationLine(models.Model):
    _name = 'sell.quotation.line'

    quotation_id = fields.Many2one('sell.quotation',
                                   string=u'报价单',
                                   required=True,
                                   ondelete='cascade')
    partner_id = fields.Many2one('partner',
                                 related='quotation_id.partner_id',
                                 string=u'客户',
                                 readonly=1,
                                 store=True)
    date = fields.Date(string=u'报价日期',
                       related='quotation_id.date',
                       readonly=1,
                       store=True)
    state = fields.Selection(related='quotation_id.state',
                             string=u'确认状态',
                             readonly=1)
    goods_id = fields.Many2one('goods',
                               string=u'产品',
                               required=True)
    price = fields.Float(u'报价(含税)', digits=dp.get_precision('Price'))
    qty = fields.Float(u'起订量', digits=dp.get_precision('Quantity'))
    uom_id = fields.Many2one('uom',
                             ondelete='restrict',
                             string=u'计量单位',
                             required=True)

    @api.multi
    @api.onchange('goods_id')
    def onchange_goods_id(self):
        ''' 当订单行的商品变化时，带出商品上的计量单位、含税价 '''
        if self.goods_id:
            self.uom_id = self.goods_id.uom_id
            # 报价单行单价取之前确认的报价单 #1795
            last_quo = self.search([('goods_id', '=', self.goods_id.id),
                                    ('partner_id', '=', self.quotation_id.partner_id.id),
                                    ('state', '=', 'done')], order='date desc', limit=1)
            self.price = last_quo and last_quo.price or self.goods_id.price


class SellOrderLine(models.Model):
    _inherit = 'sell.order.line'

    quotation_line_id = fields.Many2one('sell.quotation.line', string=u'报价单行')

    price_taxed = fields.Float(u'含税单价',
                               digits=dp.get_precision('Price'),
                               store=True,
                               related='quotation_line_id.price',
                               help=u'含税单价，取商品零售价')
    quantity = fields.Float(u'数量',
                            default=0,
                            required=True,
                            digits=dp.get_precision('Quantity'),
                            help=u'下单数量')

    @api.multi
    @api.onchange('quantity')
    def onchange_quantity(self):
        ''' 当订单行的商品变化时，带出报价单 '''
        if self.quantity:
            rec = self.env['sell.quotation.line'].search([('goods_id', '=', self.goods_id.id),
                                                          ('partner_id', '=', self.order_id.partner_id.id),
                                                          ('state', '=', 'done'),
                                                          ('qty', '<=', self.quantity)],
                                                         order='date desc')
            self.quotation_line_id = False
            if not rec:
                raise UserError(u'客户%s商品%s不存在已确认的起订量低于%s的报价单！' % (self.order_id.partner_id.name, self.goods_id.name, self.quantity))

            if rec:
                self.quotation_line_id = rec[0].id
