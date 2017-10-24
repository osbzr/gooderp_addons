# -*- coding: utf-8 -*-
{
    'name': 'GoodERP Portal',
    'author': "开阖软件",
    'category': 'Website',
    'summary': 'Account Management Frontend for your Customers',
    'version': '1.0',
    'description': """
Allows your customers to manage their account from a beautiful web interface.
        """,
    'depends': [
        'website',
        'core',
    ],
    'data': [
        'views/portal_view.xml',
        'views/good_portal_templates.xml',
    ],
}
