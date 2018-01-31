# -*- coding: utf-8 -*-
{
    "name": "good_process",
    "version": '11.11',
    "author": '上海开阖软件有限公司',
    "website": "http://www.osbzr.com",
    "category": "gooderp",
    "description": """
    可配置的审批流程
    """,
    "data": [
        'data/data.xml',
        'views/good_process.xml',
        'security/ir.model.access.csv',
    ],
    "depends": [
        'core',
    ],
    'qweb': [
        'static/src/xml/approver.xml',
    ],
}
