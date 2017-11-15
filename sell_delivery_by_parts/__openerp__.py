# -*- coding: utf-8 -*-
{
    'name': "GoodERP Sell Delivery by Parts模块",
    'author': "开阖软件",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    'summary': 'GoodERP组合销售',
    "description":
    '''
                        该模块实现了 GoodERP 销售组合产品时自动出货子产品的功能。
    ''',
    'version': '11.11',
    'application': True,
    'depends': ['sell'],
    'data': [
        'views/sell_delivery_parts_view.xml',
    ],
    'demo': [
    ]
}
