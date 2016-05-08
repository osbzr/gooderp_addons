# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
import simplejson
import os
import sys
import jinja2
from xml.etree import ElementTree
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

if hasattr(sys, 'frozen'):
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'html'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('openerp.addons.mobile', 'html')

env = jinja2.Environment('<%', '%>', '${', '}', '%', loader=loader, autoescape=True)


class MobileSupport(http.Controller):
    @http.route('/mobile', auth='public')
    def index(self):
        template = env.get_template('index.html')
        return template.render({
            'menus': request.env['mobile.view'].search_read(
                fields=['name', 'icon_class', 'display_name'])
        })

    def _get_model(self, name):
        view = request.env['mobile.view'].search([('name', '=', name)])
        return request.env[view.model]

    def _get_fields_list(self, name):
        view = request.env['mobile.view'].search([('name', '=', name)])
        tree = ElementTree.parse(StringIO(view.arch.encode('utf-8')))
        attribs = [node.attrib for node in tree.findall('.//tree/field')]

        def get_name(index):
            return attribs[index].get('name', '')

        def get_string(index):
            return attribs[index].get('string', '')

        headers = {
            'left': get_name(0),
            'center': get_name(1),
            'right': get_name(2),
        }

        fields = {
            'left': get_string(0),
            'center': get_string(1),
            'right': get_string(2),
        }

        return headers, fields

    def _get_form_fields_list(self, name):
        view = request.env['mobile.view'].search([('name', '=', name)])
        tree = ElementTree.parse(StringIO(view.arch.encode('utf-8')))

        return [{node.attrib.get('name'): node.attrib.get('string')}
                for node in tree.findall('.//form/field')]

    def _get_format_domain(self, domain):
        return [(
            item.get('name'),
            item.get('operator') or 'ilike',
            item.get('operator') and float(item.get('word')) or item.get('word')
        ) for item in domain]

    def _get_order(self, name, order):
        return ''

    def _parse_int(self, val):
        try:
            return int(val)
        except:
            return 0

    @http.route('/mobile/get_lists', auth='public')
    def get_lists(self, name, options):
        options = simplejson.loads(options)

        model_obj = self._get_model(name)
        if options.get('tree', 'tree') == 'tree':
            fields, headers = self._get_fields_list(name)
            domain = self._get_format_domain(options.get('domain', ''))
            print '------------options---------------'
            print domain
            order = self._get_order(name, options.get('order', ''))

            return request.make_response(simplejson.dumps({
                'headers': headers,
                'values': [{
                    'left': record.get(fields.get('left')),
                    'center': record.get(fields.get('center')),
                    'right': record.get(fields.get('right')),
                } for record in model_obj.search_read(
                    domain=domain, fields=fields.values(),
                    offset=self._parse_int(options.get('offset', 0)),
                    limit=self._parse_int(options.get('limit', 20)), order=order)]
            }))
        else:
            fields = self._get_form_fields_list(name)
            return request.make_response(simplejson.dumps({
                'headers': fields,
                'values': model_obj.browse(self._parse_int(options.get(record_id))).read(fields.keys()),
            }))

    @http.route('/mobile/get_search_view', auth='public')
    def get_search_view(self, name):
        view = request.env['mobile.view'].search([('name', '=', name)])
        tree = ElementTree.parse(StringIO(view.arch.encode('utf-8')))

        return request.make_response(simplejson.dumps(
            [dict(node.attrib, column=view.column_type(
                node.attrib.get('name', ''))) for node in tree.findall('.//form/field')]
        ))
