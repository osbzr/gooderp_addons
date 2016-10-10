{
    'name': 'GoodErp 首页设置',
    'version': '1.0',
    'author':"开阖静静<gilbert@osbzr.com>(开阖出品)",
    'summary': '首页配置',
    'category': 'Tools',
    'description':
        """
        用于实现可配置的首页系统.
        """,
    'data': [
        'security/groups.xml',
        "home_page.xml",
        'security/ir.model.access.csv',
    ],
    'depends': ['base','mail'],
    'demo': ['test_demo.xml'],
    'qweb': ['static/src/xml/*.xml'],
}
