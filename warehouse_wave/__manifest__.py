# -*- coding: utf-8 -*-
{
    'name': '捡货单和打包',
    'version': '11.11',
    'author': "上海开阖软件有限公司",
    'summary': ' ',
    'category': 'gooderp',
    'description':
    '''
        捡货单的生成
        打印,删除,及货物的打包.
    ''',
    'data': [
        'security/ir.model.access.csv',
        'views/wave.xml',
        'views/express_menu.xml',
        'data/data.xml',
        'report/report.xml',
        'views/assets_backend.xml'
    ],
    'depends': ['warehouse', 'sell'],
    'qweb': [
        'static/src/xml/*.xml',
    ],
}
