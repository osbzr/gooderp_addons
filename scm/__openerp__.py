# -*- coding: utf-8 -*-
{
    'name': "GOODERP SCM模块",
    'author': "开阖软件",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    'summary': 'GoodERP贸易行业解决方案',
    "description":
    '''
                        该模块实现了 GoodERP 按需补货的功能。

                        根据商品的现有库存及最低库存量，结合购货订单、采购入库单、销货订单、销售出库单、其他出入库单等，自动计算出商品的购货订单或者组装单。
    ''',
    'version': '11.11',
    'application': True,
    'depends': ['sell', 'buy', 'web_stock_query', 'asset', 'task'],
    'data': [
        'security/ir.model.access.csv',
        'data/stock_request_data.xml',
        'views/stock_request_view.xml',
    ],
    'demo': [
        'data/demo.xml',
    ]
}
