# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of web_readonly_bypass,
#     an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     web_readonly_bypass is free software:
#     you can redistribute it and/or modify it under the terms of the GNU
#     Affero General Public License as published by the Free Software
#     Foundation,either version 3 of the License, or (at your option) any
#     later version.
#
#     web_readonly_bypass is distributed
#     in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#     even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#     PURPOSE.  See the GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with web_readonly_bypass.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Web Error Dialog',
    'version': '11.11',
    "author": "zhengXiang",
    "website": "http://www.osbzr.com",
    'category': 'Technical Settings',
    'depends': ['web'],
    'data': [
        'views/assets_backend.xml',
    ],
    'description':
    """
        给前端报错添加一个自定义的按钮
    """,
    'installable': True,
    'auto_install': False,
}
