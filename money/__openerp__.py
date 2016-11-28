# -*- coding: utf-8 -*-
{
    'name': "GOODERP 出纳模块",
    'author': "judy@osbzr.com",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description":
    '''
                            该模块实现了 GoodERP 中 出纳 的功能。

                            通过创建收付款单，审核后来完成预收预付的功能；如果有结算单明细行，可以完成核销的功能。
                            可以查看所有结算单。
                            通过创建核销单，审核后完成核销的功能，包括预收冲应收、预付冲应付、应收冲应付、应收转应收、应付转应付几种业务类型。
                            通过创建其他收支出单，审核后完成其他收支的功能。
                            通过创建资金转账单，审核后完成资金转账的功能。

                            出纳管理的报表有：
                                    客户对账单；
                                    供应商对账单；
                                     现金银行报表；
                                     其他收支明细。
    ''',
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
