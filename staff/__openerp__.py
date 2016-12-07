# -*- coding: utf-8 -*-
{
    'name': "GOODERP HR模块",
    'author': "开阖软件",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description":
    '''
                            该模块实现了 GoodERP 中人力资源的功能。
    ''',
    'version': '11.11',
    'depends': ['base','core','finance'],
    'demo': [
             'tests/staff_demo.xml'
        ],
    'data': [
             'security/ir.model.access.csv',
             'security/groups.xml',
             'staff.xml',
             'leave.xml',
             'mail_data.xml',
        ],
}
