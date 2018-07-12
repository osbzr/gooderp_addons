# -*- coding: utf-8 -*-
# Copyright 2018 上海开阖软件 ((http://www.osbzr.com).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'GOODERP 商品编码唯一',
    'version': '11.11',
    'author': '上海开阖软件',
    'maintainer': 'False',
    'website': 'http://www.osbzr.com',
    'category': 'gooderp',
    'summary': '商品编号必输且不可重复',
    'description': """为了解决商品编号可能重复的问题""",
    'depends': [
        'goods',
    ],
    # always loaded
    'data': [
        'views/goods_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'installable': True,
    'application': False,
}
