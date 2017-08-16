# -*- coding: utf-8 -*-
{
    'name': 'GoodERP Portal Money',
    'author': "开阖软件",
    'category': 'Website',
    'summary': 'Account Management Frontend for your Customers',
    'version': '1.0',
    'description': """
Allows your customers to manage their account from a beautiful web interface.
        """,
    'depends': [
        'good_portal',
        'money',
    ],
    'data': [
        'views/good_portal_get_templates.xml',
        'views/good_portal_pay_templates.xml'
    ],
}
