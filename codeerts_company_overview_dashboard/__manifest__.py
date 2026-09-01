{
    'name': 'Company Overview Dashboard | Odoo All in One Business Analytics | Cross-App KPIs | Executive Command Center',
    'version': '19.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Free cross-app executive overview: live KPIs and trends across Sales, Purchase, Accounting, Inventory, Manufacturing, CRM, Project, POS and Expenses. Tiles appear automatically for the apps you have installed.',
    'author': 'CODEerts',
    'website': 'https://www.codeerts.com',
    'support': 'support@codeerts.com',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'codeerts_company_overview_dashboard/static/lib/apexcharts/apexcharts.min.js',
            'codeerts_company_overview_dashboard/static/src/dashboard/dashboard.scss',
            'codeerts_company_overview_dashboard/static/src/dashboard/dashboard.js',
            'codeerts_company_overview_dashboard/static/src/dashboard/dashboard.xml',
        ],
    },
    'images': ['static/description/banner.gif', 'static/description/overview.png', 'static/description/drilldown.png', 'static/description/dark.png'],
    'application': True,
    'installable': True,
}
