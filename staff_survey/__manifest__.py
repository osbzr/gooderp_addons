# -*- coding: utf-8 -*-
# Copyright 2018 上海开阖软件 ((http://www.osbzr.com).)

{
    'name': 'GOODERP 招聘问卷',
    'version': '11.11',
    'author': '上海开阖软件',
    'website': 'http://www.osbzr.com',
    'category': 'gooderp',
    'summary': '招聘问卷',
    'description': """在招聘流程中使用问卷表格""",
    'depends': [
        'staff_hire', 'survey',
    ],
    'data': [
        'views/hire_applicant_view.xml',
        'views/staff_job_view.xml',
    ],
    'demo': ['tests/demo.xml',

    ],
    'installable': True,
    'application': False,
}
