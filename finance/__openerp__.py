# -*- coding: utf-8 -*-
{
    'name': "GOODERP 会计模块",
    'author': "开阖软件(开阖Jason 开阖静静gilbert@osbzr.com and 社区的贡献)",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    用于实现gooderp中会计 使用的大部分功能.
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
        'home_page_data.xml',
        'voucher_template.xml',
        'issue_cost_wizard.xml',
        'report_auxiliary_accounting.xml',
    ],
    'demo': [
        'tests/finance_demo.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
