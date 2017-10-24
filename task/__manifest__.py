# -*- coding: utf-8 -*-
{
    'name': "GOODERP Task",

    'summary': """
        使用 GTD 理念支持员工记录日常工作进度 """,

    'description':
    '''
                        该模块实现了 GoodERP 中 任务管理 的功能。

                        将project拆分成task，并将task分配到人。每个人每天一张 timesheet 记录每个 task 的执行过程。
    ''',

    'author': "开阖软件",
    'website': "http://www.osbzr.com",

    'category': 'gooderp',
    'version': '11.11',

    'depends': ['money'],

    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        'security/rules.xml',
        'views/views.xml',
        'data/data.xml',
        'data/home_page.xml'
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
}
