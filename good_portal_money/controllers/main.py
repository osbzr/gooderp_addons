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
        money_order_obj = request.env['money.order']
        partner = request.env.user.gooderp_partner_id

        # 付款单
        pay_count = money_order_obj.search_count([
            ('partner_id', '=', partner.id),
            ('type', '=', 'get')
        ])
        response.qcontext.update({
            'pay_count': pay_count,
        })

        # 收款单
        get_count = money_order_obj.search_count([
            ('partner_id', '=', partner.id),
            ('type', '=', 'pay')
        ])
        response.qcontext.update({
            'get_count': get_count,
        })
        return response

    #
    # Pay Orders
    #
    @http.route(['/my/pay/orders', '/my/pay/orders/page/<int:page>'], type='http', auth="user", website=True)
    def my_pay_orders(self, page=1, date_begin=None, date_end=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.gooderp_partner_id
        money_order_obj = request.env['money.order']

        domain = [
            ('partner_id', '=', partner.id),
            ('type', '=', 'get')
        ]
        archive_groups = self._get_archive_groups('money.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        pay_count = money_order_obj.search_count(domain)
        # pager
        pager = request.website.pager(
            url="/my/pay/orders",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=pay_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        pay_orders = money_order_obj.search(
            domain, limit=self._items_per_page, offset=pager['offset'])
#         print "pay_orders", pay_orders
        values.update({
            'date': date_begin,
            'pay_orders': pay_orders,
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/pay/orders',
        })
        print "vaules", values
        return request.render("good_portal_money.portal_my_pay_orders", values)

    @http.route(['/my/pay/orders/<int:order>'], type='http', auth="user", website=True)
    def pay_orders_followup(self, order=None, **kw):
        pay_order = request.env['money.order'].browse([order])
        try:
            pay_order.check_access_rights('read')
            pay_order.check_access_rule('read')
        except AccessError:
            return request.render("website.403")

        pay_order_sudo = pay_order.sudo()
        return request.render("good_portal_money.pay_orders_followup", {
            'pay_order': pay_order_sudo,
        })

    #
    # Get Orders
    #
    @http.route(['/my/get/orders', '/my/get/orders/page/<int:page>'], type='http', auth="user", website=True)
    def my_get_orders(self, page=1, date_begin=None, date_end=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.gooderp_partner_id
        money_order_obj = request.env['money.order']

        domain = [
            ('partner_id', '=', partner.id),
            ('type', '=', 'pay')
        ]
        archive_groups = self._get_archive_groups('money.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        get_count = money_order_obj.search_count(domain)
        # pager
        pager = request.website.pager(
            url="/my/get/orders",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=get_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        get_orders = money_order_obj.search(
            domain, limit=self._items_per_page, offset=pager['offset'])
#         print "pay_orders", pay_orders
        values.update({
            'date': date_begin,
            'get_orders': get_orders,
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/get/orders',
        })
        print "vaules", values
        return request.render("good_portal_money.portal_my_get_orders", values)

    @http.route(['/my/get/orders/<int:order>'], type='http', auth="user", website=True)
    def get_orders_followup(self, order=None, **kw):
        get_order = request.env['money.order'].browse([order])
        try:
            get_order.check_access_rights('read')
            get_order.check_access_rule('read')
        except AccessError:
            return request.render("website.403")

        get_order_sudo = get_order.sudo()
        return request.render("good_portal_money.get_orders_followup", {
            'get_order': get_order_sudo,
        })
