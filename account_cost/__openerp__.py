# -*- coding: utf-8 -*-
{
    'name': "GOODERP 服务采购模块",
    'author': "德清武康开源软件工作室",
    'website': "www.gooderp.org",
    'category': 'gooderp',
    'summary': '该模块实现了服务采购过程中费用结算管理的功能，并可将费用按入库金额分摊至不同的入库单。',
    "description":
    '''
    该模块实现了服务采购过程中费用通结算管理的功能，并可将费用按入库金额分摊至不同的出入库单。
    ''',
    'version': '11.11',
    'depends': ['buy'],
    'data': [
        'views/cost_order_view.xml',
        'views/cost_action.xml',
        'views/cost_menu.xml',
        'security/ir.model.access.csv',
        'security/cost_sequence.xml',
    ],
    'demo': [
        'data/cost_order_demo.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
    'license': 'AGPL-3',
}
