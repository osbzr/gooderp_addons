# -*- coding: utf-8 -*-
{
    'name': '外部视图引入',
    'version': '11.11',
    'author': 'gilbert(静静)',
    'website': '',
    'summary': '引入外部js重置视图',
    'category': 'js',
    'description':
    '''
    ''',
    'depends': ['web'],
    'data': [
        'views/webclient_templates.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'application': True,
}
