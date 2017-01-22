# -*- coding: utf-8 -*-
{
    'name': "gooderp_weixin",

    'summary': u"""
        gooderp 微信企业号 基本应用""",

    'description': u"""
        微信企业号接入
    """,

    'author': "nbzx",
    'website': "http://odoo.nbzx.me",


    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', "gooderp_wechat", "auth_oauth", 'website', 'staff'],

    #
    'installable': True,

    # always loaded
    'data': [
        'views/weixin_setting_view.xml',
        'data/gooderp_corp_weixin.xml',
        'views/weixin_enterprise_view.xml',
        'views/weixin_contacts_view.xml',
        'views/auth_oauth_provider_view.xml',
        'security/ir.model.access.csv',
        'templates.xml',
        'wizard/weixin_sync_content_view.xml',
        'wizard/weixin_diff_contacts_view.xml',
    ],
}
