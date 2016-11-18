# -*- coding: utf-8 -*-
{
    'name': "GOODERP SCM模块",
    'author': "开阖软件",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    'summary': 'GoodERP贸易行业解决方案',
    "description": """
    用于GoodERP进销存的核心功能.
    """,
    'version': '11.11',
    'application':True,
    'depends': ['core', 'sell', 'buy', 'warehouse'],
    'data': [
             'security/ir.model.access.csv',
             'data/stock_request_data.xml',
             'view/stock_request_view.xml',
             ]
}
