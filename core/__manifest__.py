# -*- coding: utf-8 -*-
{
    'name': "GOODERP 核心模块",
    'author': "开阖软件",
    'summary': '隐藏Odoo内置技术复杂性，增加基本权限组',
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description":
    '''
                          该模块是 gooderp 的核心模块，完成了基本表的定义和配置。

                           定义了基本类，如 partner,bank_account,goods,staff,uom等；
                           定义了基本配置： 用户、类别等；
                           定义了高级配置： 系统参数、定价策略。
    ''',
    'version': '11.11',
    'depends': ['report',
                'web_menu_create',
                'decimal_precision',
                'web_export_view_good',
                'home_page',
                'web_error_dialog',
                'common_dialog',
                'app_odoo_customize',
                ],
    'demo': [
        'data/core_demo.xml',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/core_data.xml',
        'data/ir_config_parameter.xml',
        'views/core_view.xml',
        'views/core_templates.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
}
