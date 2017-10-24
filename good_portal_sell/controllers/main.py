# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.good_portal.controllers.main import website_account


class WebsiteAccount(website_account):

    @http.route()
    def account(self, **kw):
        """ Add sales documents to main account page """
        response = super(WebsiteAccount, self).account(**kw)
        partner = request.env.user.gooderp_partner_id

        # 销售单
        sell_order_obj = request.env['sell.order']
        order_count = sell_order_obj.search_count([
            ('partner_id', '=', partner.id)
        ])
        response.qcontext.update({
            'order_count': order_count,
        })
        return response

    #
    # Sell Orders
    #
    @http.route(['/my/orders', '/my/orders/page/<int:page>'], type='http', auth="user", website=True)
    def my_orders(self, page=1, date_begin=None, date_end=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.gooderp_partner_id
        SaleOrder = request.env['sell.order']

        domain = [
            ('partner_id', '=', partner.id)
        ]
        archive_groups = self._get_archive_groups('sell.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        order_count = SaleOrder.search_count(domain)
        # pager
        pager = request.website.pager(
            url="/my/orders",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        orders = SaleOrder.search(
            domain, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'orders': orders,
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/orders',
        })
        return request.render("good_portal_sell.portal_my_orders", values)

    @http.route(['/my/orders/<int:order>'], type='http', auth="user", website=True)
    def orders_followup(self, order=None, **kw):
        order = request.env['sell.order'].browse([order])
        try:
            order.check_access_rights('read')
            order.check_access_rule('read')
        except AccessError:
            return request.render("website.403")

        order_sudo = order.sudo()

        return request.render("good_portal_sell.orders_followup", {
            'order': order_sudo,
        })
