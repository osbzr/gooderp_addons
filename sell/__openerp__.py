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
    'name': 'GOODERP 销售模块',
    'author': 'jeff@osbzr.com,flora@osbzr.com',
    'website': 'https://www.osbzr.com',
    'description': '''gooderp销售实例，通过安装gooderp模块展示odoo的销售流程''',
    'category': 'gooderp',
    'version': '11.11',
    'depends': ['core', 'warehouse', 'money', 'partner_address', 'staff'],
    'data': [
            'data/sell_data.xml',
            'security/groups.xml',
            'views/sell_view.xml',
            'report/customer_statements_view.xml',
            'report/sell_order_track_view.xml',
            'report/sell_order_detail_view.xml',
            'report/sell_summary_goods_view.xml',
            'report/sell_summary_partner_view.xml',
            'report/sell_summary_staff_view.xml',
            'report/sell_receipt_view.xml',
            'report/sell_top_ten_view.xml',
            'wizard/customer_statements_wizard_view.xml',
            'wizard/sell_order_track_wizard_view.xml',
            'wizard/sell_order_detail_wizard_view.xml',
            'wizard/sell_summary_goods_wizard_view.xml',
            'wizard/sell_summary_partner_wizard_view.xml',
            'wizard/sell_summary_staff_wizard_view.xml',
            'wizard/sell_receipt_wizard_view.xml',
            'wizard/sell_top_ten_wizard_view.xml',
            'security/ir.model.access.csv',
            'report/report_data.xml',
            'data/home_page_data.xml'
            ],
    'demo': [
             'data/sell_demo.xml',
             ],
    'installable': True,
    'auto_install': False,
}
