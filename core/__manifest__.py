# -*- coding: utf-8 -*-
{
    'name': "GOODERP 核心模块",
    'author': "开阖软件",
    'summary': '隐藏Odoo内置技术复杂性，增加基本权限组',
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    """,
    'version': '11.11',
    'depends': ['base',
                'web_menu_create',
                'decimal_precision',
                'web_export_view_good',
                'home_page',
                'common_dialog'],
    'demo': [
        'data/core_demo.xml',
        ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/core_data.xml',
        'views/core_view.xml',
        'views/core_templates.xml',
        ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
}
