##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 Therp BV <http://therp.nl>.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "Open a dashboard's action",
    "version": "10.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Hidden",
    "summary": "Adds a button to open a dashboard in full mode",
    "depends": [
        'board',
    ],
    "data": [
        'views/templates.xml',
    ],
    "qweb": [
        'static/src/xml/web_dashboard_open_action.xml',
    ],
    "test": [
    ],
    "auto_install": False,
    'installable': True,
    "application": False,
    "external_dependencies": {
        'python': [],
    },
}
