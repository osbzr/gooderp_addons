# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.odoo.com>).
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
    "name": "GOODERP Goods Management",
    "version": '11.11',
    "author": 'ZhengXiang',
    "website": "http://www.osbzr.com",
    "category": "gooderp",
    "depends": ['core'],
    "description":
    '''
                     该模块继承自 core 模块，进一步扩展定义了商品及其相关的类。
    ''',
    "data": [
        'security/groups.xml',
        'view/goods_view.xml',
        'view/goods_class_view.xml',
        'view/goods_data.xml',
        'action/goods_action.xml',
        'menu/goods_menu.xml',
        'security/ir.model.access.csv',
    ],
    'demo': ['demo/goods_demo.xml'],
    'installable': True,
    "active": False,
}
