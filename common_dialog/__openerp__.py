# -*- coding: utf-8 -*-
{
    "name": "Common Dialog",
    "version": '11.11',
    "author": 'ZhengXiang',
    "website": "http://www.osbzr.com",
    "category": "Generic Modules",
    "description": """
        添加一个通用的wizard，可以被函数调用
        在新API里面的model里面调用 open_dialog(func, options=None)函数，其中

        - @func: 函数名称字符串，属于当前model的函数
        - @options：一个字典，里面可以传入一些具体参数
            - @message: 向导的具体内容
            - @args：调用函数的时候传入的args参数
            - @kwargs：调用函数的时候传入的kwargs参数，func(*args, **kwargs)
    """,
    "data": [
        'wizard/wizard_view.xml',
    ],
    'installable': True,
    "active": False,
}
