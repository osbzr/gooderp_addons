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
    'author': "开阖静静<gilbert@osbzr.com>(开阖出品), MAXodoo<9842766@qq.com>",
    "depends": ['web'],
    'description':
    '''对于分组Grouping显示模式，展开关闭分组行时，重新锁定表头的代码还需要完善。
    ''',
    'data': [
        'views/fixed_header.xml',
    ],
    'installable': True,
}
