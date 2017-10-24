# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, models, fields, tools
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SellOrder(models.Model):
    _inherit = "sell.order"

    website_order_line = fields.One2many('sell.order.line',
                                         'order_id',
                                         string=u'显示在网页上的发货订单行',
                                         readonly=True
                                         )
    cart_quantity = fields.Integer(compute='_compute_cart_info',
                                   string=u'购物车产品数量')
    only_services = fields.Boolean(
        compute='_compute_cart_info', string='Only Services')

    @api.multi
    @api.depends('website_order_line.quantity', 'website_order_line.goods_id')
    def _compute_cart_info(self):
        ''' 计算购物车产品数量 '''
        for order in self:
            order.cart_quantity = int(
                sum(order.mapped('website_order_line.quantity')))
            order.only_services = all(
                l.goods_id.not_saleable for l in order.website_order_line)

    @api.model
    def _get_website_data(self, order):
        return {
            'partner': order.partner_id.id,
            'order': order
        }

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, attributes=None, **kwargs):
        self.ensure_one()
        attribute_id = self._get_line_attribute(
            line_id, product_id, attributes=attributes)

        domain = [('order_id', '=', self.id), ('goods_id', '=',
                                               product_id), ('attribute_id', '=', attribute_id)]
        if line_id:
            domain += [('id', '=', line_id)]

        return self.env['sell.order.line'].sudo().search(domain)

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0):
        # 获取创建订单行需要的数据
        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)

        product_context.update({
            'partner': order.partner_id.id,
            'quantity': qty,
            'date': order.date,
        })
        product = self.env['goods'].sudo().with_context(
            product_context).browse(product_id)

        return {
            'goods_id': product_id,
            'quantity': qty,
            'order_id': order_id,
            'uom_id': product.uom_id.id,
            'price': product.price,
        }

    @api.multi
    def _get_line_attribute(self, order_id, product_id, attributes=None):
        # 获取 属性
        if not attributes:
            return

        product_context = dict(self.env.context)
        product = self.env['goods'].with_context(
            product_context).browse(product_id)

        # 属性：attribute-48-颜色，48是 product_id, 颜色是属性值的 category
        web_value_lists = []
        for k, v in attributes.items():
            if len(k.split('-')) > 2:
                attribute_category = self.env['core.category'].sudo().search(
                    [('name', '=', k.split('-')[2])])
                attribute_value_value = self.env['attribute.value.value'].sudo().search([('name', '=', v),
                                                                                         ('category_id', '=', attribute_category.id)])
                web_value_lists.append(attribute_value_value.id)

        attribute_id = False
        for attribute in product.attribute_ids:
            goods_value_lists = []
            for value in attribute.value_ids:
                goods_value_lists.append(value.value_id.id)
            if goods_value_lists == web_value_lists:  # 找到产品属性里匹配用户 web 界面输入的属性
                attribute_id = attribute.id
                break

        return attribute_id

    @api.multi
    def _get_line_description(self, order_id, product_id):
        # 获取创建订单行需要的 描述
        product_context = dict(self.env.context)
        product = self.env['goods'].with_context(
            product_context).browse(product_id)
        name = product.display_name

        if product.note:
            name += '\n%s' % (product.note)
        return name

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, attributes=None, **kwargs):
        """ 添加或者设置产品数量 """
        self.ensure_one()
        sell_order_line_sudo_obj = self.env['sell.order.line'].sudo()
        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(u'请先新建销售订单')

        if line_id is not False:
            order_lines = self._cart_find_product_line(
                product_id, line_id, attributes=attributes, **kwargs)
            order_line = order_lines and order_lines[0]

        # 不存在产品的销售明细行，则新建
        if not order_line:
            values = self._website_product_id_change(
                self.id, product_id, qty=1)  # 获取创建订单行需要的数据
            # 获取创建订单行的 属性
            values['attribute_id'] = self._get_line_attribute(
                self.id, product_id, attributes=attributes)
            values['note'] = self._get_line_description(
                self.id, product_id)  # 获取创建订单行的 备注
            order_line = sell_order_line_sudo_obj.create(values)

            if add_qty:
                add_qty -= 1

        # compute new quantity
        if set_qty:
            quantity = set_qty
        elif add_qty is not None:
            quantity = order_line.quantity + (add_qty or 0)

        # Remove zero of negative lines
        if quantity <= 0:
            order_line.unlink()
        else:
            # update line
            values = self._website_product_id_change(
                self.id, product_id, qty=quantity)
            if not self.env.context.get('fixed_price'):
                order = self.sudo().browse(self.id)
                product_context = dict(self.env.context)

                product_context.update({
                    'partner': order.partner_id.id,
                    'quantity': quantity,
                    'date': order.date,
                })

            order_line.write(values)

        return {'line_id': order_line.id, 'quantity': quantity}


class Website(models.Model):
    _inherit = 'website'

#     pricelist_id = fields.Many2one('product.pricelist', compute='_compute_pricelist_id', string='Default Pricelist')
#     currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', string='Default Currency')
    salesperson_id = fields.Many2one('res.users', string=u'销售员')
#     salesteam_id = fields.Many2one('crm.team', string='Sales Team')

    @api.multi
    def _prepare_sale_order_values(self, partner):
        ''' 创建销售订单数据 '''
        self.ensure_one()
#         affiliate_id = request.session.get('affiliate_id')
#         salesperson_id = affiliate_id if self.env['res.users'].sudo().browse(affiliate_id).exists() else request.website.salesperson_id.id
#         addr = partner.address_get(['delivery', 'invoice'])
#         default_user_id = partner.parent_id.user_id.id or partner.user_id.id
        values = {
            'partner_id': partner.id,
            'currency_id': self.env.user.company_id.currency_id.id,
            #             'payment_term_id': self.sale_get_payment_term(partner),
            #             'team_id': self.salesteam_id.id,
            #             'partner_invoice_id': partner.id,
            #             'partner_shipping_id': partner.id,
            #             'user_id': salesperson_id or self.salesperson_id.id or default_user_id,
            'warehouse_id': self.env['warehouse'].sudo().search([('type', '=', 'stock')], limit=1, order='id asc').id
        }

        company = self.company_id
        if company:
            values['company_id'] = company.id

        return values

    # 生成销售订单
    @api.multi
    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        """ Return the current sale order after mofications specified by params.
        :param bool force_create: Create sale order if not already existing
        :param str code: Code to force a pricelist (promo code)
                         If empty, it's a special case to reset the pricelist with the first available else the default.
        :param bool update_pricelist: Force to recompute all the lines from sale order to adapt the price with the current pricelist.
        :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one
        :returns: browse record for the current sale order
        """
        self.ensure_one()
        # 客户
        partner = self.env.user.gooderp_partner_id
        if not partner:
            partner = self.env['partner'].sudo().create({
                'name': self.env.user.name,
                'c_category_id': self.env.ref('good_shop.portal_customer_category').id,
                'main_mobile': '123456789',
            })
            self.env.user.gooderp_partner_id = partner.id

        sale_order_id = request.session.get('sale_order_id')
        if not sale_order_id:
            last_order = partner.last_website_so_id
            # Do not reload the cart of this user last visit if the cart is no longer draft or uses a pricelist no longer available.
            sale_order_id = last_order.state == 'draft' and last_order.id

        # Test validity of the sale_order_id
        sale_order = self.env['sell.order'].sudo().browse(
            sale_order_id).exists() if sale_order_id else None

        # 创建销售订单
        if not sale_order and (force_create or code):
            # TODO cache partner_id session
            so_data = self._prepare_sale_order_values(partner)
            sale_order = self.env['sell.order'].sudo().create(so_data)

            sale_order.pre_receipt = sale_order.amount
            request.session['sale_order_id'] = sale_order.id

            if request.website.gooderp_partner_id.id != partner.id:
                partner.write({'last_website_so_id': sale_order.id})

        if sale_order:
            # case when user emptied the cart
            if not request.session.get('sale_order_id'):
                request.session['sale_order_id'] = sale_order.id

            # check for change of partner_id ie after signup
            if sale_order.partner_id.id != partner.id and request.website.gooderp_partner_id.id != partner.id:
                # 改变客户，并触发 onchange_partner_id
                sale_order.write({'partner_id': partner.id})
                sale_order.onchange_partner_id()

            sale_order.write({'pre_receipt': sale_order.amount})
        else:
            request.session['sale_order_id'] = None
            return None

        return sale_order

    def sale_reset(self):
        request.session.update({
            'sale_order_id': False,
            'sale_transaction_id': False,
            'website_sale_current_pl': False,
        })

    @api.multi
    def sell_order_to_delivery(self):
        sell_order_id = request.session.get('sale_order_id')
        SellOrder = self.env['sell.order'].sudo().search(
            [('id', '=', sell_order_id)])
        if SellOrder:
            if SellOrder.pre_receipt and not sell_order.bank_account_id:
                if not self.env.user.company_id.bank_account_id:
                    SellOrder.bank_account_id = self.env.ref(
                        'good_shop.web_company_bank').id
                else:
                    SellOrder.bank_account_id = self.env.user.sudo().company_id.bank_account_id.id
            SellOrder.sell_order_done()


class ResPartner(models.Model):
    _inherit = 'partner'

    last_website_so_id = fields.Many2one('sell.order', string=u'客户最近一次的销售发货单')
