# -*- coding: utf-8 -*-
{
    'name': "员工报销模块",
    'author': "德清武康开源软件工作室",
    'website': "无",
    'category': 'gooderp',
    "description":
    '''
                        该模块为员工报销模块
    ''',
    'version': '11.11',
    'depends': ['base', 'core', 'finance', 'money', 'staff'],
    'data': [
        'data/expense_data.xml',
        'view/assets_backend.xml',
        'view/hr_expense_view.xml',
        'view/hr_expense_action.xml',
        'view/hr_expense_menu.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'tests/staff_expense_demo.xml'
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
