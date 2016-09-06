{
    'name': 'GoodErp 首页设置',
    'version': '1.0',
    'author': "开阖-静静gilbert@osbzr.com",
    'summary': '首页配置',
    'category': 'Tools',
    'description':
        """
        用于实现可配置的首页系统.
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
