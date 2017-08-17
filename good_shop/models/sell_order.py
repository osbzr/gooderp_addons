# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random

from odoo import api, models, fields, tools
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class sell_delivery(models.Model):
    _inherit = "sell.delivery"

    website_order_line = fields.One2many(related='sell_move_id.line_out_ids',
                                         relation='wh.move.line',
                                         string=u'显示在网页上的发货订单行',
                                         readonly=True
                                         )
    cart_quantity = fields.Integer(compute='_compute_cart_info',
                                   string=u'购物车产品数量')
#     payment_acquirer_id = fields.Many2one('payment.acquirer', string='Payment Acquirer', copy=False)
#     payment_tx_id = fields.Many2one('payment.transaction', string='Transaction', copy=False)
    only_services = fields.Boolean(compute='_compute_cart_info', string='Only Services')

    @api.multi
    @api.depends('website_order_line.goods_qty', 'website_order_line.goods_id')
    def _compute_cart_info(self):
        ''' 计算购物车产品数量 '''
        for order in self:
            order.cart_quantity = int(sum(order.mapped('website_order_line.goods_qty')))
            order.only_services = all(l.goods_id.not_saleable for l in order.website_order_line)

    @api.model
    def _get_errors(self, order):
        return []

    @api.model
    def _get_website_data(self, order):
        return {
            'partner': order.partner_id.id,
            'order': order
        }

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        self.ensure_one()
        product = self.env['goods'].browse(product_id)

        # split lines with the same product if it has untracked attributes
#          and product.mapped('attribute_ids').filtered(lambda r: not r.attribute_id.create_variant) and not line_id
#         if product and not line_id:
#             print "product000", product
#             return self.env['sell.order.line']

        domain = [('move_id', '=', self.sell_move_id.id), ('goods_id', '=', product_id)]
        if line_id:
            domain += [('id', '=', line_id)]
        return self.env['wh.move.line'].sudo().search(domain)

    @api.multi
    def _website_product_id_change(self, delivery, product_id, qty=0):
        order = self.sudo().browse(delivery.id)
        product_context = dict(self.env.context)

        product_context.update({
            'partner': order.partner_id.id,
            'goods_qty': qty,
            'date': order.date,
        })
        product = self.env['goods'].sudo().with_context(product_context).browse(product_id)

        return {
            'goods_id': product_id,
            'goods_qty': qty,
            'move_id': delivery.sell_move_id.id,
            'uom_id': product.uom_id.id,
            'price_taxed': product.price,
            'type': 'out',
#             'attribute_id': product.attribute_ids and product.attribute_ids[0].value_ids or False
        }

    @api.multi
    def _get_line_description(self, order_id, product_id, attributes=None):
        if not attributes:
            attributes = {}

        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)

        product = self.env['goods'].with_context(product_context).browse(product_id)

        name = product.display_name

        # add untracked attributes in the name
        untracked_attributes = []
        for _, v in attributes.items():
            # attribute should be like 'attribute-48-1' where 48 is the product_id, 1 is the attribute_id and v is the attribute value
            attribute_value = self.env['attribute.value'].sudo().browse(int(v))
            if attribute_value:
                untracked_attributes.append(attribute_value.name)
        if untracked_attributes:
            name += '\n%s' % (', '.join(untracked_attributes))

        if product.note:
            name += '\n%s' % (product.note)

        return name

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, attributes=None, **kwargs):
        """ 添加或者设置产品数量 """
        self.ensure_one()
        SaleOrderLineSudo = self.env['wh.move.line'].sudo()
        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(u'请先新建销售订单')

        if line_id is not False:
            order_lines = self._cart_find_product_line(product_id, line_id, **kwargs)
            order_line = order_lines and order_lines[0]

        # 不存在产品的销售明细行，则新建
        if not order_line:
            values = self._website_product_id_change(self, product_id, qty=1)
#             values['note'] = self._get_line_description(self.id, product_id, attributes=attributes)
            order_line = SaleOrderLineSudo.create(values)

            if add_qty:
                add_qty -= 1

        # compute new quantity
        if set_qty:
            quantity = set_qty
        elif add_qty is not None:
            quantity = order_line.goods_qty + (add_qty or 0)

        # Remove zero of negative lines
        if quantity <= 0:
            order_line.unlink()
        else:
            # update line
            values = self._website_product_id_change(self, product_id, qty=quantity)
            if not self.env.context.get('fixed_price'):
                order = self.sudo().browse(self.id)
                product_context = dict(self.env.context)

                product_context.update({
                    'partner': order.partner_id.id,
                    'goods_qty': quantity,
                    'date': order.date,
                })
                product = self.env['goods'].with_context(product_context).browse(product_id)
#                 values['price_unit'] = self.env['account.tax']._fix_tax_included_price(
#                     order_line._get_display_price(product),
#                     order_line.product_id.taxes_id,
#                     order_line.tax_id
#                 )

            order_line.write(values)

        return {'line_id': order_line.id, 'goods_qty': quantity}

    def _cart_accessories(self):
        """ Suggest accessories based on 'Accessory Products' of products in cart """
        for order in self:
            accessory_products = order.website_order_line.mapped('product_id.accessory_product_ids').filtered(lambda product: product.website_published)
            accessory_products -= order.website_order_line.mapped('product_id')
            return random.sample(accessory_products, len(accessory_products))


class Website(models.Model):
    _inherit = 'website'

#     pricelist_id = fields.Many2one('product.pricelist', compute='_compute_pricelist_id', string='Default Pricelist')
#     currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', string='Default Currency')
    salesperson_id = fields.Many2one('res.users', string=u'销售员')
#     salesteam_id = fields.Many2one('crm.team', string='Sales Team')
#     pricelist_ids = fields.One2many('product.pricelist', compute="_compute_pricelist_ids",
#                                     string='Price list available for this Ecommerce/Website')

    @api.one
    def _compute_pricelist_ids(self):
        self.pricelist_ids = self.env["product.pricelist"].search([("website_id", "=", self.id)])

    @api.multi
    def _compute_pricelist_id(self):
        for website in self:
            if website._context.get('website_id') != website.id:
                website = website.with_context(website_id=website.id)
            website.pricelist_id = website.get_current_pricelist()

    # This method is cached, must not return records! See also #8795
    @tools.ormcache('self.env.uid', 'country_code', 'show_visible', 'website_pl', 'current_pl', 'all_pl', 'partner_pl', 'order_pl')
    def _get_pl_partner_order(self, country_code, show_visible, website_pl, current_pl, all_pl, partner_pl=False, order_pl=False):
        """ Return the list of pricelists that can be used on website for the current user.
        :param str country_code: code iso or False, If set, we search only price list available for this country
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :param int website_pl: The default pricelist used on this website
        :param int current_pl: The current pricelist used on the website
                               (If not selectable but the current pricelist we had this pricelist anyway)
        :param list all_pl: List of all pricelist available for this website
        :param int partner_pl: the partner pricelist
        :param int order_pl: the current cart pricelist
        :returns: list of pricelist ids
        """
        pricelists = self.env['product.pricelist']
        if country_code:
            for cgroup in self.env['res.country.group'].search([('country_ids.code', '=', country_code)]):
                for group_pricelists in cgroup.pricelist_ids:
                    if not show_visible or group_pricelists.selectable or group_pricelists.id in (current_pl, order_pl):
                        pricelists |= group_pricelists

        partner = self.env.user.partner_id
        is_public = self.user_id.id == self.env.user.id
        if not is_public and (not pricelists or (partner_pl or partner.property_product_pricelist.id) != website_pl):
            if partner.property_product_pricelist.website_id:
                pricelists |= partner.property_product_pricelist

        if not pricelists:  # no pricelist for this country, or no GeoIP
            pricelists |= all_pl.filtered(lambda pl: not show_visible or pl.selectable or pl.id in (current_pl, order_pl))
        else:
            pricelists |= all_pl.filtered(lambda pl: not show_visible and pl.sudo().code)

        # This method is cached, must not return records! See also #8795
        return pricelists.ids

    def _get_pl(self, country_code, show_visible, website_pl, current_pl, all_pl):
        pl_ids = self._get_pl_partner_order(country_code, show_visible, website_pl, current_pl, all_pl)
        return self.env['product.pricelist'].browse(pl_ids)

    def get_pricelist_available(self, show_visible=False):

        """ Return the list of pricelists that can be used on website for the current user.
        Country restrictions will be detected with GeoIP (if installed).
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :returns: pricelist recordset
        """
        website = request and request.website or None
        if not website:
            if self.env.context.get('website_id'):
                website = self.browse(self.env.context['website_id'])
            else:
                website = self.search([], limit=1)
        isocountry = request and request.session.geoip and request.session.geoip.get('country_code') or False
        partner = self.env.user.partner_id
        order_pl = partner.last_website_so_id and partner.last_website_so_id.state == 'draft' and partner.last_website_so_id.pricelist_id
        partner_pl = partner.property_product_pricelist
        pricelists = website._get_pl_partner_order(isocountry, show_visible,
                                                   website.user_id.sudo().partner_id.property_product_pricelist.id,
                                                   request and request.session.get('website_sale_current_pl') or None,
                                                   website.pricelist_ids,
                                                   partner_pl=partner_pl and partner_pl.id or None,
                                                   order_pl=order_pl and order_pl.id or None)
        return self.env['product.pricelist'].browse(pricelists)

    def is_pricelist_available(self, pl_id):
        """ Return a boolean to specify if a specific pricelist can be manually set on the website.
        Warning: It check only if pricelist is in the 'selectable' pricelists or the current pricelist.
        :param int pl_id: The pricelist id to check
        :returns: Boolean, True if valid / available
        """
        return pl_id in self.get_pricelist_available(show_visible=False).ids

    def get_current_pricelist(self):
        """
        :returns: The current pricelist record
        """
        # The list of available pricelists for this user.
        # If the user is signed in, and has a pricelist set different than the public user pricelist
        # then this pricelist will always be considered as available
        available_pricelists = self.get_pricelist_available()
        pl = None
        partner = self.env.user.partner_id
        if request and request.session.get('website_sale_current_pl'):
            # `website_sale_current_pl` is set only if the user specifically chose it:
            #  - Either, he chose it from the pricelist selection
            #  - Either, he entered a coupon code
            pl = self.env['product.pricelist'].browse(request.session['website_sale_current_pl'])
            if pl not in available_pricelists:
                pl = None
                request.session.pop('website_sale_current_pl')
        if not pl:
            # If the user has a saved cart, it take the pricelist of this cart, except if
            # the order is no longer draft (It has already been confirmed, or cancelled, ...)
            pl = partner.last_website_so_id.state == 'draft' and partner.last_website_so_id.pricelist_id
            if not pl:
                # The pricelist of the user set on its partner form.
                # If the user is not signed in, it's the public user pricelist
                pl = partner.property_product_pricelist
            if available_pricelists and pl not in available_pricelists:
                # If there is at least one pricelist in the available pricelists
                # and the chosen pricelist is not within them
                # it then choose the first available pricelist.
                # This can only happen when the pricelist is the public user pricelist and this pricelist is not in the available pricelist for this localization
                # If the user is signed in, and has a special pricelist (different than the public user pricelist),
                # then this special pricelist is amongs these available pricelists, and therefore it won't fall in this case.
                pl = available_pricelists[0]

        if not pl:
            _logger.error('Fail to find pricelist for partner "%s" (id %s)', partner.name, partner.id)
        return pl

    @api.multi
    def sale_product_domain(self):
        return [("sale_ok", "=", True)]

    @api.model
    def sale_get_payment_term(self, partner):
        DEFAULT_PAYMENT_TERM = 'account.account_payment_term_immediate'
        return partner.property_payment_term_id.id or self.env.ref(DEFAULT_PAYMENT_TERM, False).id

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
#             'partner_invoice_id': addr['invoice'],
#             'partner_shipping_id': addr['delivery'],
#             'user_id': salesperson_id or self.salesperson_id.id or default_user_id,
            'warehouse_id': self.env['warehouse'].sudo().search([('type', '=', 'stock')], limit=1, order='id asc').id
        }

        company = self.company_id
        if company:
            values['company_id'] = company.id

        return values

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
        sale_order = self.env['sell.delivery'].sudo().browse(sale_order_id).exists() if sale_order_id else None

        # 创建销售订单
        if not sale_order and (force_create or code):
            # TODO cache partner_id session
            so_data = self._prepare_sale_order_values(partner)
            sale_order = self.env['sell.delivery'].sudo().create(so_data)

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
#                 sale_order.onchange_partner_shipping_id() # fiscal position
#                 sale_order['payment_term_id'] = self.sale_get_payment_term(partner)

        else:
            request.session['sale_order_id'] = None
            return None

        return sale_order

    def sale_get_transaction(self):
        tx_id = request.session.get('sale_transaction_id')
        if tx_id:
            transaction = self.env['payment.transaction'].sudo().browse(tx_id)
            # Ugly hack for SIPS: SIPS does not allow to reuse a payment reference, even if the
            # payment was not not proceeded. For example:
            # - Select SIPS for payment
            # - Be redirected to SIPS website
            # - Go back to eCommerce without paying
            # - Be redirected to SIPS website again => error
            # Since there is no link module between 'website_sale' and 'payment_sips', we prevent
            # here to reuse any previous transaction for SIPS.
            if transaction.state != 'cancel' and transaction.acquirer_id.provider != 'sips':
                return transaction
            else:
                request.session['sale_transaction_id'] = False
        return False

    def sale_reset(self):
        request.session.update({
            'sale_order_id': False,
            'sale_transaction_id': False,
            'website_sale_current_pl': False,
        })


class ResPartner(models.Model):
    _inherit = 'partner'

    last_website_so_id = fields.Many2one('sell.delivery', string=u'客户最近一次的销售发货单')
