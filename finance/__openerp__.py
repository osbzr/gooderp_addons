# -*- coding: utf-8 -*-
{
    'name': "GOODERP 会计模块",
    'author': "开阖软件",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    """,
    'version': '8.0.0.1',
    'depends': ['base', 'decimal_precision', 'core', 'num_to_china'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/finance_voucher_data.xml',
        'data/finance_data.xml',
        'data/finance_export_template_data.xml',
        'res_config_view.xml',
        'finance_conf.xml',
        'wizard/checkout_wizard.xml',
        'finance_view.xml',
        'company.xml',
        'trial_balance.xml',
        'report/report_voucher.xml',
        'balance_sheet.xml',

    ],
    'demo': [
        'tests/finance_demo.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
