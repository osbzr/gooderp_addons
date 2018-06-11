# -*- coding: utf-8 -*-
{
    'name': "GOODERP 税务模块-进项发票",
    'author': "德清武康开源软件工作室",
    'website': "无",
    'category': 'gooderp',
    "description":
    '''
                        该模块实现了导入认证系统的进项发票。
    ''',
    'version': '11.11',
    'depends': ['scm', 'cn_account_invoice'],
    'data': [
        'view/tax_invoice_in_view.xml',
        'view/tax_invoice_in_action.xml',
        'view/tax_invoice_in_menu.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
