# -*- coding: utf-8 -*-
{
    'name': "gooderp_wechat",
    'summary': u"""
        微信sdk和framework7""",
    'description': u"""
    开阖出品
    """,
    'author': "nbzx, 开阖静静等",
    'website': "http://www.gooderp.org/",
    'category': 'Uncategorized',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': [],
    'installable': True,
    # always loaded
    'data': [
        'wizard/sycn_menu_wizard_view.xml',
        'views/wechat_menu_view.xml',
        'views/wechat_permission_group_view.xml',
        'views/wechat_application_view.xml',
        'views/wechat_enterprise_view.xml',
        'security/ir.model.access.csv',
    ],
}
