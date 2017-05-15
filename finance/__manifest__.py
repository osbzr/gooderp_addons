# -*- coding: utf-8 -*-
{
    'name': "GOODERP 会计模块",
    'author': "开阖软件(开阖Jason 开阖静静gilbert@osbzr.com and 社区的贡献)",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description":
    '''
                          该模块实现了 GoodERP 中 会计 的功能。

                           可以创建新的会计凭证；
                           可以定义会计凭证模板；
                           可以进行月末结账；
                           可以查看月末凭证变更记录。

                           会计实现的报表有：
                                分录查询；
                                科目余额表；
                                资产负债表；
                                利润表；
                                发出成本；
                                科目明细账；
                                科目总账；
                                辅助核算余额表。
    ''',
    'depends': ['num_to_china', 'web_sublist', 'good_process', 'ir_sequence_autoreset'],
    'version': '11.11',
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/finance_voucher_data.xml',
        'data/finance_data.xml',
        'data/finance_export_template_data.xml',
        'views/res_config_view.xml',
        'views/finance_conf.xml',
        'wizard/checkout_wizard.xml',
        'views/finance_view.xml',
        'views/company.xml',
        'views/trial_balance.xml',
        'report/report_voucher.xml',
        'views/balance_sheet.xml',
        'data/home_page_data.xml',
        'data/voucher_template.xml',
        'views/issue_cost_wizard.xml',
        'views/report_auxiliary_accounting.xml',
        'views/exchange.xml',
    ],
    'demo': [
        'tests/finance_demo.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
