# -*- coding: utf-8 -*-
{
    'name': "GOODERP Task",

    'summary': """
        使用 GTD 理念支持员工记录日常工作进度 """,

    'description': """
        将project拆分成task，并将task分配到人。每个人每天一张timesheet记录每个task的执行过程
    """,

    'author': "开阖软件",
    'website': "http://www.osbzr.com",

    'category': 'gooderp',
    'version': '11.11',

    'depends': ['core', 'money'],

    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        'views/views.xml',
        'views/templates.xml',
        'data/data.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'application':True,
}