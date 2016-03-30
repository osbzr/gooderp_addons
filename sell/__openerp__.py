# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2014 上海开阖软件有限公司 (http://www.osbzr.com). 
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
{
    'name':'GOODERP 销售模块',
    'author':'jeff@osbzr.com,jacky@osbzr.com',
    'website': 'https://www.osbzr.com',
    'description': '''gooderp销售实例，通过安装gooderp模块展示openerp的销售流程''',
    'depends':['base','mail','core','warehouse'],
    'data':[
            'sell_view.xml',
            'sell_data.xml',
            ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
