# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import tools

from odoo.fields import Date


class website_account(http.Controller):

    MANDATORY_BILLING_FIELDS = ["main_contact", "main_mobile", 'message']

    _items_per_page = 20

    def _prepare_portal_layout_values(self):
        """ prepare the values to render portal layout """
        partner = request.env.user.gooderp_partner_id
        # get customer sales rep
        if partner:
            sales_rep = request.env.user
        else:
            sales_rep = False
        values = {
            'sales_rep': sales_rep,
            'company': request.website.company_id,
            'user': request.env.user
        }
        return values

    def _get_archive_groups(self, model, domain=None, fields=None, groupby="create_date", order="create_date desc"):
        if not model:
            return []
        if domain is None:
            domain = []
        if fields is None:
            fields = ['name', 'create_date']
        groups = []
        for group in request.env[model]._read_group_raw(domain, fields=fields, groupby=groupby, orderby=order):
            dates, label = group[groupby]
            date_begin, date_end = dates.split('/')
            groups.append({
                'date_begin': Date.to_string(Date.from_string(date_begin)),
                'date_end': Date.to_string(Date.from_string(date_end)),
                'name': label,
                'item_count': group[groupby + '_count']
            })
        return groups

    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def account(self, **kw):
        values = self._prepare_portal_layout_values()

        return request.render("good_portal.portal_my_home", values)

    @http.route(['/my/account'], type='http', auth='user', website=True)
    def details(self, redirect=None, **post):
        partner = request.env.user.gooderp_partner_id
        values = {
            'error': {},
            'error_message': []
        }

        if post:
            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                values = {key: post[key]
                          for key in self.MANDATORY_BILLING_FIELDS}

                partner.sudo().write(values)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        values.update({
            'partner': partner,
            'redirect': redirect,
        })

        return request.render("good_portal.details", values)

    def details_form_validate(self, data):
        error = dict()
        error_message = []

        # Validation
        for field_name in self.MANDATORY_BILLING_FIELDS:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # error message for empty required fields
        if [err for err in error.values() if err == 'missing']:
            error_message.append(u'必输字段不能为空')

        unknown = [k for k in data.iterkeys(
        ) if k not in self.MANDATORY_BILLING_FIELDS]
        if unknown:
            error['common'] = 'Unknown field'
            error_message.append(u"未知字段 '%s'" % ','.join(unknown))

        return error, error_message
