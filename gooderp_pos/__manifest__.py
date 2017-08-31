# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'GOODERP POS',
    'version': '11.11',
    'author': "上海开阖软件有限公司",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    'sequence': 20,
    'summary': 'pos',
    'description': """
        简单POS系统
    """,
    'depends': ['sell'],
    'data': [
        'security/gooderp_pos_security.xml',
        'security/ir.model.access.csv',
        'views/pos_session_view.xml',
        'views/pos_templates.xml',
        'views/gooderp_pos.xml',
        'views/pos_config_view.xml',
        'views/pos_order_view.xml',
        'views/goods_view.xml',
        'views/pos_dashboard.xml',
        'data/gooderp_pos_data.xml',
    ],
    'demo': [
        'data/gooderp_pos_demo.xml',
    ],
    'installable': True,
    'application': True,
    'qweb': ['static/src/xml/pos.xml'],
}
