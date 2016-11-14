# -*- coding: utf-8 -*-
{
    'name': "GOODERP HR模块",
    'author': "开阖软件",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description": """
    """,
    'version': '11.11',
    'depends': ['base','core'],
    'demo': [
             'tests/staff_demo.xml'
        ],
    'data': [
             'security/ir.model.access.csv',
             'security/groups.xml',
             'staff.xml',
             'mail_data.xml',
        ],
}
