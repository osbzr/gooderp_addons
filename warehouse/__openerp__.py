# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
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
    "name": "GOODERP Warehouse Management",
    "version": "0.1",
    "author": 'ZhengXiang',
    "website": "http://www.osbzr.com",
    "category": "Generic Modules",
    "depends": ['core', 'goods', 'mobile', 'decimal_precision', 'web_sublist', 'web_float_limit', 'web_readonly_bypass'],
    "description": """
    """,
    "data": [
        'data/warehouse_data.xml',
        'security/groups.xml',
        'wizard/save_bom_view.xml',
        'wizard/stock_transceive_wizard_view.xml',
        'wizard/lot_track_wizard_view.xml',
        'view/assets_backend.xml',
        'view/warehouse_view.xml',
        'view/inventory_view.xml',
        'view/production_view.xml',
        'view/goods_view.xml',
        'report/stock_balance_view.xml',
        'report/stock_transceive_view.xml',
        'report/lot_status_view.xml',
        'report/lot_track_view.xml',
        'action/warehouse_action.xml',
        'menu/warehouse_menu.xml',
        'data/sequence.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/warehouse_demo.xml',
     ],
     'qweb': [
        'data/copy_move_line.xml',
    ],
    'installable': True,
    "active": False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
