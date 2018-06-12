# -*- coding: utf-8 -*-
{
    'name': "GOODERP 税务模块-销项发票",
    'author': "德清武康开源软件工作室",
    'website': "无",
    'category': 'gooderp',
    "description":
    '''
                       模块为从金税系统导出开票内容，导入系统后，自动生成销售订单，出库单，结算单。
    ''',
    'version': '11.11',
    'depends': ['scm','cn_account_invoice'],
    'data': [
        'view/tax_invoice_out_view.xml',
        'view/tax_invoice_out_action.xml',
        'view/tax_invoice_out_menu.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'tests/demo.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
