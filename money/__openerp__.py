# -*- coding: utf-8 -*-
{
    'name': "GOODERP 出纳模块",
    'author': "judy@osbzr.com",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    """,
    'version': '11.11',
    'depends': ['core', 'base', 'finance', 'report_docx'],
    'data': [
        'data/money_data.xml',
        'security/groups.xml',
        'view/money_order_view.xml',
        'view/other_money_order_view.xml',
        'view/money_transfer_order_view.xml',
        'view/reconcile_order_view.xml',
        'data/money_sequence.xml',
        'wizard/partner_statements_wizard_view.xml',
        'report/bank_statements_view.xml',
        'wizard/bank_statements_wizard_view.xml',
        'report/other_money_statements_view.xml',
        'wizard/other_money_statements_wizard_view.xml',
        'security/ir.model.access.csv',
        'view/partner_view.xml',
        'generate_accounting.xml',
        'home_page_data.xml',
        'report/report_data.xml',
    ],
    'demo': [
        'money_demo.xml',
    ],
}
