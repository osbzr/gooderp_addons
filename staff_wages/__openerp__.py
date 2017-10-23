# -*- coding: utf-8 -*-
{
    'name': "GOODERP 工资模块",
    'author': "德清武康开源软件工作室",
    'website': "无",
    'category': 'gooderp',
    "description":
    '''
                        该模块为工资模块，可计提工资，工资可以二个提取，月末一次计提，次月（发放前）一次补提一次！
    ''',
    'version': '11.11',
    'depends': ['staff', 'money'],
    'data': [
        'views/wages_view.xml',
        'views/wages_action.xml',
        'views/wages_menu.xml',
        'data/wages_data.xml',
        'security/ir.model.access.csv',
        'report/wages_report.xml',
        'report/wages_templates.xml',
    ],
    'demo': [
        'demo/staff_wages_demo.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
