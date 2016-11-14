# -*- coding: utf-8 -*-
{
    'name': "GOODERP 采购模块",
    'author': "flora@osbzr.com",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    """,
    'version': '11.11',
    'depends': ['core', 'warehouse', 'money', 'finance'],
    'data': [
        'data/buy_data.xml',
        'security/groups.xml',
        'views/buy_order_view.xml',
        'views/buy_receipt_view.xml',
        'views/buy_adjust_view.xml',
        'views/buy_action.xml',
        'views/buy_menu.xml',
        'views/vendor_goods_view.xml',
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
        'report/report_data.xml',
        'security/ir.model.access.csv',
        'data/home_page_data.xml'
        ],
    'demo': [
             'data/buy_demo.xml',
             ],
}
