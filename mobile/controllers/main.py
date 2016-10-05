# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.tools.safe_eval import safe_eval as eval
import simplejson
import os
import sys
import jinja2
import werkzeug
from xml.etree import ElementTree
from odoo.modules.registry import RegistryManager
from contextlib import closing
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

if hasattr(sys, 'frozen'):
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'html'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.mobile', 'html')

env = jinja2.Environment('<%', '%>', '${', '}', '%', loader=loader, autoescape=True)


class MobileSupport(http.Controller):
    @http.route('/mobile/login', type='http', auth='none')
    def login(self, db_choose=''):
        db_list = http.db_list() or []
        db_list_by_mobile = []
        for db in db_list:
            db_manager = RegistryManager.get(db)
            with closing(db_manager.cursor()) as cr:
                cr.execute('''
                           SELECT id FROM ir_module_module
                           WHERE state = 'installed' AND name = 'mobile'
                           ''')
                if cr.fetchall():
                    db_list_by_mobile.append(db)

        template = env.get_template('login.html')
        return template.render({'db_list': db_list_by_mobile, 'db_choose': db_choose})

    @http.route('/mobile/db_login', auth='none')
    def db_login(self, db, account, passwd):
        request.session.db = db
        uid = request.session.authenticate(request.session.db, account, passwd)

        if uid is not False:
            return 'ok'

        return '错误的帐号或密码'

    @http.route('/mobile', type='http', auth='none')
    def index(self):
        if not request.db or not request.session.uid:
            return werkzeug.utils.redirect('/mobile/login')

        return werkzeug.utils.redirect('/mobile/home')

    @http.route('/mobile/home', auth='public')
    def home(self):
        if not request.db or not request.session.uid:
            return werkzeug.utils.redirect('/mobile/login')

        template = env.get_template('index.html')
        return template.render({
            'menus': request.env['mobile.view'].search_read(
                fields=['name', 'icon_class', 'display_name', 'using_wizard'])
        })

    def _get_model(self, name):
        view = request.env['mobile.view'].search([('name', '=', name)])
        return request.env[view.model]

    def _get_fields_list(self, name):
        view = request.env['mobile.view'].search([('name', '=', name)])
        tree = ElementTree.parse(StringIO(view.arch.encode('utf-8')))
        attribs = [node.attrib for node in tree.findall('.//tree/field')]

        return {
            'left': dict(attribs[0], column=view.column_type(attribs[0].get('name', ''))),
            'center': dict(attribs[1], column=view.column_type(attribs[1].get('name', ''))),
            'right': dict(attribs[2], column=view.column_type(attribs[2].get('name', ''))),
        }

    def _get_form_fields_list(self, name):
        view = request.env['mobile.view'].search([('name', '=', name)])
        tree = ElementTree.parse(StringIO(view.arch.encode('utf-8')))

        return {node.attrib.get('name'): dict(node.attrib, column=view.column_type(node.attrib.get('name', '')))
                for node in tree.findall('.//form/field')}

    def _get_format_domain(self, name, domain):
        view = request.env['mobile.view'].search([('name', '=', name)])
        res = view.domain and eval(view.domain) or []
        res.extend([(
            item.get('name'),
            item.get('operator') or 'ilike',
            item.get('operator') and float(item.get('word')) or item.get('word')
        ) for item in domain])

        return res

    def _get_order(self, name, order):
        if len(order.split()) == 2:
            return order
        return ''

    def _parse_int(self, val):
        try:
            return int(val)
        except:
            return 0

    def _get_max_count(self, name, domain):
        # 可以考虑写成SQL语句来提高性能
        view = request.env['mobile.view'].search([('name', '=', name)])
        return len(request.env[view.model].search(domain))

    def _get_limit(self, name):
        view = request.env['mobile.view'].search([('name', '=', name)])
        return view.limit or 20

    @http.route('/mobile/get_lists', auth='public')
    def get_lists(self, name, options):
        options = simplejson.loads(options)

        model_obj = self._get_model(name)
        if options.get('type', 'tree') == 'tree':
            headers = self._get_fields_list(name)
            domain = self._get_format_domain(name, options.get('domain', ''))
            order = self._get_order(name, options.get('order', ''))
            limit = self._get_limit(name)

            return request.make_response(simplejson.dumps({
                'headers': headers,
                'max_count': self._get_max_count(name, domain),
                'values': [{
                    'left': record.get(headers.get('left').get('name')),
                    'center': record.get(headers.get('center').get('name')),
                    'right': record.get(headers.get('right').get('name')),
                    'id': record.get('id'),
                } for record in model_obj.with_context(options.get('context') or {}).search_read(
                    domain=domain, fields=map(lambda field: field.get('name'), headers.values()),
                    offset=self._parse_int(options.get('offset', 0)), limit=limit, order=order)]
            }))
        else:
            headers = self._get_form_fields_list(name)
            return request.make_response(simplejson.dumps([{
                'name': key,
                'value': value,
                'string': headers.get(key, {}).get('string'),
                'column': headers.get(key, {}).get('column'),
            } for key, value in model_obj.with_context(options.get('context') or {}).browse(self._parse_int(
                options.get('record_id'))).read(headers.keys())[0].iteritems()
            ]))

    @http.route('/mobile/get_search_view', auth='public')
    def get_search_view(self, name):
        view = request.env['mobile.view'].search([('name', '=', name)])
        tree = ElementTree.parse(StringIO(view.arch.encode('utf-8')))

        return request.make_response(simplejson.dumps(
            [dict(node.attrib, column=view.column_type(
                node.attrib.get('name', ''))) for node in tree.findall('.//search/field')]
        ))

    @http.route('/mobile/get_wizard_view', auth='public')
    def get_wizard_view(self, name):
        view = request.env['mobile.view'].search([('name', '=', name)])
        tree = ElementTree.parse(StringIO(view.arch.encode('utf-8')))

        return request.make_response(simplejson.dumps(
            [dict(node.attrib, value='') for node in tree.findall('.//wizard/field')]
        ))

    @http.route('/mobile/many2one/search', auth='public')
    def many2one_search(self, word, model, domain):
        return request.make_response(simplejson.dumps([
            {
            'id': record[0], 'value': record[1]
            } for record in request.env[model].name_search(
                word, args=eval(domain), limit=20)
        ]))
