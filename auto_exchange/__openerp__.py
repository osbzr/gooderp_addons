# -*- coding: utf-8 -*-
{
    'name': "GOODERP 自动取汇率模块",
    'author': "德清武康开源软件工作室",
    'website': "无",
    'category': 'gooderp',
    "description":
    '''
                        该模块实现了自动取汇率的功能。
    ''',
    'version': '11.11',
    'depends': ['money'],
    'data': [
        'view/auto_exchange_view.xml',
        'view/auto_exchange_action.xml',
        'view/auto_exchange_menu.xml',
        'security/ir.model.access.csv',
        'security/auto_exchange_data.xml',
    ],
    'demo': [
        'tests/demo.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
