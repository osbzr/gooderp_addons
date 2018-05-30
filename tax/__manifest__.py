# -*- coding: utf-8 -*-
{
    'name': "GOODERP 税务模块",
    'author': "德清武康开源软件工作室",
    'website': "无",
    'category': 'gooderp',
    "description":
    '''
                        该模块为税务基础模块
    ''',
    'version': '11.11',
    'depends': ['core', 'finance', 'goods',],
    'data': [
        'view/tax_res_config_view.xml',
        'view/tax_config_view.xml',
        'view/tax_config_action.xml',
        'view/tax_config_menu.xml',
        'security/ir.model.access.csv',
        'data/tax_code.xml',
        'data/automatic_cost.xml',
    ],
    'demo': [
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
