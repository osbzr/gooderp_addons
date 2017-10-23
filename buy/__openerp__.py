# -*- coding: utf-8 -*-
{
    'name': "GOODERP 采购模块",
    'author': "flora@osbzr.com",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description":
    '''
                            该模块可以方便的管理购货。

                            通过创建购货订单，审核后从供应商那里采购购货订单行中的商品，来完成购货功能。
                            通过创建购货退货订单，审核后将购货订单行中的商品退回给供应商，来完成购货退货功能。
                            通过创建采购变更单，选择原始购货订单，审核后将采购变更单行中的商品调整到原始购货订单行，来完成采购调整功能。

                            购货管理的报表有：
                                 采购订单跟踪表；
                                 采购明细表；
                                 采购汇总表（按商品、按供应商）；
                                 采购收款一览表。
    ''',
    'version': '11.11',
    'depends': ['warehouse', 'partner_address'],
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
