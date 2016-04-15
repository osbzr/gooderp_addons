# -*- coding: utf-8 -*-
{
    'name': "GOODERP 会计模块",
    'author': "开阖软件",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    """,
    'version': '8.0.0.1',
    'depends': ['base', 'decimal_precision','core'],
    'demo': [
             'tests/finance_demo.xml',
        ],
    'data': [
        'security/ir.model.access.csv',
        'data/finance_data.xml',
        'finance_conf.xml',
        'finance_view.xml',
        ],
}