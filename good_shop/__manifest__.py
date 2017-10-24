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
        'good_portal',
        'core',
        'sell',
        'money',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/good_shop_templates.xml',
        'views/goods_view.xml',
    ],
}
