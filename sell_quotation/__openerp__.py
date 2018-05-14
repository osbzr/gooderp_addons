# -*- coding: utf-8 -*-
{
    'name': "GoodERP Sell Quotation模块",
    'author': "开阖软件",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    'summary': 'GoodERP报价单',
    "description":
    '''
                        该模块实现了 GoodERP 给客户报价的功能。
    ''',
    'version': '11.11',
    'application': True,
    'depends': ['sell','good_crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/sell_quotation_view.xml',
        'data/sell_quotation_data.xml',
        'report/report_data.xml',
    ],
    'demo': [
        'data/demo.xml',
    ]
}
