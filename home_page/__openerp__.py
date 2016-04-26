{
    'name': 'GoodErp 首页设置',
    'version': '1.0',
    'summary': '首页配置',
    'category': 'Tools',
    'description':
        """

        """,
    'data': [
        'security/groups.xml',
        "home_page.xml",
        "home_data.xml",
        'security/ir.model.access.csv',
    ],
    'depends': ['base', 'buy', 'warehouse', 'sell'],
    'demo': ['test_demo.xml'],
    'qweb': ['static/src/xml/*.xml'],
    'application': True,
}
