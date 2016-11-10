# -*- coding: utf-8 -*-
{
    'name': "GOODERP 资产模块",
    'author': "德清武康开源软件工作室",
    'website': "无",
    'category': 'gooderp',
    "description": """
        实现平均年限法的固定资产初始化，采购，变更，处理。
    """,
    'version': '11.11',
    'depends': ['base', 'finance', 'money'],
    'data': [
        'view/asset.xml',
        'view/asset_action.xml',
        'view/asset_menu.xml',
        'data/asset_data.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/asset_demo.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
