# -*- coding: utf-8 -*-
{
    'name': 'GoodERP Portal Task',
    'author': "开阖软件",
    'category': 'Website',
    'summary': 'Portal Task',
    'version': '1.0',
    'description': """
Allows your partners to manage their account from a beautiful web interface.
        """,
    'depends': [
        'good_portal',
        'task',
    ],
    'data': [
        'views/good_portal_task_templates.xml',
    ],
}
