# -*- coding: utf-8 -*-
{
    'name': "GOODERP 税务模块-发票管理",
    'author': "德清武康开源软件工作室",
    'website': "无",
    'category': 'gooderp',
    "description":
    '''
                        该模块实现中国发票的基础内容。
    ''',
    'version': '11.11',
    'depends': ['tax'],
    'data': [
        'view/cn_account_invoice_view.xml',
        'view/cn_account_invoice_action.xml',
        'view/cn_account_invoice_menu.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
