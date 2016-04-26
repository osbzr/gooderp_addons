# -*- coding: utf-8 -*-
{
    'name': "GOODERP 会计模块",
    'author': "开阖软件",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    """,
    'version': '8.0.0.1',
    'depends': ['base', 'decimal_precision', 'core', 'num_to_china'],
    'demo': [
        'tests/finance_demo.xml',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/finance_data.xml',
        'finance_conf.xml',
        'finance_view.xml',
        'trial_balance.xml',
        'balance_sheet.xml'
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
