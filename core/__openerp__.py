# -*- coding: utf-8 -*-
{
    'name': "GOODERP 核心模块",
    'author': "开阖软件",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    """,
    'version': '8.0.0.1',
    'depends': ['base',
                'web_menu_create',
                'decimal_precision',
                'web_readonly_bypass'],
    'demo': [
        'core_demo.xml',
        ],
    'data': [
        'security/groups.xml',
        'core_data.xml',
        'core_view.xml',
        'security/ir.model.access.csv',
        ],
}
