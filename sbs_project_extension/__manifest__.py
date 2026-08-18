{
    'name': 'SBS Project Extension',
    'version': '19.0.3.0.0',
    'category': 'Services/Project',
    'summary': 'Manage extended project, review, team, and financial details',
    'description': (
        'Extend Odoo Project with dedicated areas for project summaries, '
        'reviews, team engagement, client and technical information, AMC '
        'details, credentials, financial collection tracking, and a per-task '
        'work timer that logs the counted time to the task timesheet.'
    ),
    'author': 'Star Bit Solutions',
    'company': 'Star Bit Solutions',
    'maintainer': 'Star Bit Solutions',
    'website': 'https://starbitsolutions.com',
    'depends': ['project', 'hr_timesheet'],
    'data': [
        'security/sbs_project_extension_security.xml',
        'security/ir.model.access.csv',
        'security/sbs_project_extension_task_timer_security.xml',
        'wizard/sbs_project_extension_timesheet_log_views.xml',
        'views/sbs_project_extension_config_views.xml',
        'views/sbs_project_extension_project_views.xml',
        'views/sbs_project_extension_main_views.xml',
        'views/sbs_project_extension_team_engagement_views.xml',
        'views/sbs_project_extension_info_views.xml',
        'views/sbs_project_extension_financial_views.xml',
        'views/sbs_project_extension_review.xml',
        'views/sbs_project_extension_task_timer_views.xml',
        'views/sbs_project_extension_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sbs_project_extension/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'sbs_project_extension/static/tests/**/*.test.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'application': True,
}
