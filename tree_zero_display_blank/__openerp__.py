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
    'name': "零显示为空(tree页面)",
    'version': '11.11',
    'summary': """
            
    """,
    'category': 'osbzr',
    'author': "开阖静静<gilbert@osbzr.com>(开阖出品)",
    "depends": ['web'],
    'description':
    '''
                    该模块实现了在tree上面显示为零的转换为显示为空(该模块为全局设置,安装后就自动启用功能,无需加参数控制!)
                    注意:此模块功能 有可能 和其他tree 上 float 字段 上的 widegt显示 冲突!
    ''',
    'data': [
        'view/tree_zero_display_blank.xml',
    ],
    'installable': True,
}
