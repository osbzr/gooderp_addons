# -*- coding: utf-8 -*-
{
    'name': 'GoodERP Shop',
    'author': "开阖软件",
    'category': 'Website',
    'summary': 'Shop',
    'version': '1.0',
    'description': """
Allows your customers to manage their shopping from a beautiful web interface.
        """,
    'depends': [
        'website',
        'core',
        'sell',
    ],
    'data': [
             'data/data.xml',
             'views/good_shop_templates.xml',
    ],
}
