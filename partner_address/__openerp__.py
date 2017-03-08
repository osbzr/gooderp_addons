# -*- coding: utf-8 -*-
{
    'name': "GOODERP 联系人地址模块",
    'author': "judy（开阖软件）",
    'category': 'gooderp',
    'version': '11.11',
    'depends': ['core'],
    "description":
    '''
                        该模块实现了 GoodERP 中 业务伙伴地址选择 的功能。

                        包含了中国的各个省及各个城市、县；
                        实现了选择省过滤出城市，选择城市过滤出县，选择城市不属于省改变省等业务。
    ''',
    'data': [
        'data/base_data.xml',
        'data/all.city.csv',
        'data/all.county.csv',
        'views/partner_address.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
}
