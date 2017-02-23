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
    'name': "会计中数字用中文表示",
    'version': '11.11',
    'summary': """
            
    """,
    'category': 'osbzr',
    'author': "开阖静静<gilbert@osbzr.com>(开阖出品)",
    "depends": ['web', 'core'],
    'description':
    '''
                    该模块主要实现了一个widget 使得阿拉伯数字在页面上显示为中文。
    ''',
    'data': [
        'views/num_to_china.xml',
    ],
    'installable': True,
}
