# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS',
    'version': '1.0.1',
    'category': 'pos',
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
        'data/gooderp_pos_data.xml',
        'data/gooderp_pos_demo.xml',
    ],
    'demo': [
        'data/gooderp_pos_demo.xml',
    ],
    'installable': True,
    'application': True,
    'qweb': ['static/src/xml/pos.xml'],
}
