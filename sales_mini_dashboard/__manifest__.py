
{
    'name': 'Sale Mini Dashboard',
    'version': '1.2',
    'summary': 'User Can Now View Mini Dashboard in Sale Order List View',
    'sequence': 10,
    'author': "JD DEVS",
    'depends': ['base', 'sale', 'account'],
    'data': [
        "views/orders.xml",
    ],
    'assets': {
        'web.assets_backend': [
            # css
            "sales_mini_dashboard/static/src/css/sale_mini.css",
            # JS
            "sales_mini_dashboard/static/src/js/list_view_extend.js",
        ],
        'web.assets_qweb': [
            'sales_mini_dashboard/static/src/xml/list_view_extend.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'images': ['static/description/assets/screenshots/banner.png'],
}
