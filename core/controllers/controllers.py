# -*- coding: utf-8 -*-
import imghdr
import json
import functools
from odoo import http, tools
import odoo, os, sys, jinja2
from odoo.addons.web.controllers.main import Database
from odoo.addons.web.controllers.main import Home
from odoo.addons.web.controllers import main
from odoo.modules import get_resource_path
from cStringIO import StringIO
from odoo.http import request

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.core', "views")
env = main.jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = json.dumps
db_monodb = http.db_monodb


class GoodERPLogin(Home):
    @http.route('/login', type='http', auth="none")
    def login(self, db, login, key):
        return main.login_and_redirect(db, login, key)


class GoodERPDB(Database):
    def _render_template(self, **d):
        d.setdefault('manage', True)
        d['insecure'] = odoo.tools.config['admin_passwd'] == 'admin'
        d['list_db'] = odoo.tools.config['list_db']
        d['langs'] = odoo.service.db.exp_list_lang()
        d['countries'] = odoo.service.db.exp_list_countries()
        # databases list
        d['databases'] = []
        try:
            d['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            monodb = db_monodb()
            if monodb:
                d['databases'] = [monodb]
        return env.get_template("gooderp_database_manager.html").render(d)
