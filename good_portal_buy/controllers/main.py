# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.good_portal.controllers.main import website_account


class WebsiteAccount(website_account):

    @http.route()
    def account(self, **kw):
        """ 在 我的账户 主页添加 采购订单+数量 """
        response = super(WebsiteAccount, self).account(**kw)
        partner = request.env.user.gooderp_partner_id

        BuyOrder = request.env['buy.order']
        buy_order_count = BuyOrder.search_count([
            ('partner_id', '=', partner.id)
        ])

        response.qcontext.update({
            'buy_order_count': buy_order_count,
        })
        return response

    #
    # Buy Orders
    #
    @http.route(['/my/buy/orders', '/my/buy/orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_buy_orders(self, page=1, date_begin=None, date_end=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.gooderp_partner_id
        BuyOrder = request.env['buy.order']

        domain = [
            ('partner_id', '=', partner.id)
        ]
        archive_groups = self._get_archive_groups('buy.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        order_count = BuyOrder.search_count(domain)
        # pager
        pager = request.website.pager(
            url="/my/buy/orders",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        orders = BuyOrder.search(
            domain, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'orders': orders,
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/buy/orders',
        })
        return request.render("good_portal_buy.portal_my_buy_orders", values)

    @http.route(['/my/buy/orders/<int:order>'], type='http', auth="user", website=True)
    def buy_orders_followup(self, order=None, **kw):
        order = request.env['buy.order'].browse([order])
        try:
            order.check_access_rights('read')
            order.check_access_rule('read')
        except AccessError:
            return request.render("website.403")

        order_sudo = order.sudo()

        return request.render("good_portal_buy.buy_orders_followup", {
            'order': order_sudo,
        })
