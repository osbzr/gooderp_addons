# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
import simplejson
import os
import sys
import jinja2

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
        return template.render({'menus': [{'name': 'tree'}, {'name': 'form'}] * 5})

    @http.route('/mobile/get_lists', auth='public')
    def get_lists(self, name, domain, offset, limit):
        model = name.replace('_', '.')

        print '---' * 10, request

        import ipdb
        ipdb.set_trace()
        return request.make_response(simplejson.loads(
            [{'nihao': 'hello'}]
        ))
