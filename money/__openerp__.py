# -*- coding: utf-8 -*-
{
    'name': "GOODERP 会计模块",
    'author': "judy@osbzr.com",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    """,
    'version': '8.0.0.1',
    'depends': ['core', 'base'],
    'data': [
        'view/money_order_view.xml',
        'view/other_money_order_view.xml',
        'view/money_transfer_order_view.xml',
        'view/reconcile_order_view.xml',
        'data/money_sequence.xml',
        'data/money_data.xml',
        'wizard/partner_statements_wizard_view.xml',
        'report/bank_statements_view.xml',
        'wizard/bank_statements_wizard_view.xml',
        'report/other_money_statements_view.xml',
        'wizard/other_money_statements_wizard_view.xml',
        'security/ir.model.access.csv',
        'view/go_live_order_view.xml',
        'view/partner_view.xml',
        ],
    'demo': [
        'money_demo.xml',
            ],
}
