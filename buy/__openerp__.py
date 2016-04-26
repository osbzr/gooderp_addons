# -*- coding: utf-8 -*-
{
    'name': "GOODERP 采购模块",
    'author': "flora@osbzr.com",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    """,
    'version': '8.0.0.1',
    'depends': ['core', 'mail', 'warehouse', 'money'],
    'data': [
        'buy_data.xml',
        'security/groups.xml',
        'buy_view.xml',
        'wizard/buy_order_track_wizard_view.xml',
        'wizard/buy_order_detail_wizard_view.xml',
        'wizard/buy_summary_goods_wizard_view.xml',
        'wizard/buy_summary_partner_wizard_view.xml',
        'wizard/buy_payment_wizard_view.xml',
        'wizard/supplier_statements_wizard_view.xml',
        'report/buy_order_track_view.xml',
        'report/buy_order_detail_view.xml',
        'report/buy_summary_goods_view.xml',
        'report/buy_summary_partner_view.xml',
        'report/buy_payment_view.xml',
        'report/supplier_statements_view.xml',
        'security/ir.model.access.csv',
        ],
    'demo': [
             'buy_demo.xml',
             ],
}
