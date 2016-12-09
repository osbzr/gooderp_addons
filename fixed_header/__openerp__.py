# -*- coding: utf-8 -*-
# ##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Gilbert Yuan(开阖出品) (<gilbert@osbzr.com>).
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
    'name': "tree 页面固定表头模块",
    'version': '11.11',
    'summary': """
            
    """,
    'category': 'osbzr',
    'author': "开阖静静<gilbert@osbzr.com>(开阖出品)",
    "depends": ['web'],
    'description':
    '''
        此模块仅限在电脑上使用,(但是仍有局限性,仅限与常规操作,如果页面变化太快会导致表头定位不准)
        另外在手机端或者页面很小的情况下 会导致 表头挡道其他的 dom
    ''',
    'data': [
        'fixed_header.xml',
    ],
    'installable': True,
}
