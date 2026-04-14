{
    'name': 'Books',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Mini Accounting Module for Institutes',
    'description': """
        Branch based accounting for institutes.
        - Income and Expense tracking per branch.
        - Bank/UPI transactions.
        - Branch-level and centralized reporting.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'student_management', 'institute_crm'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/ir_sequence_data.xml',
        'views/dashboard_views.xml',
        'views/menu_views.xml',
        'views/type_views.xml',
        'views/transaction_views.xml',
        'views/user_views.xml',
        'views/account_views.xml',
        'views/institute_semester_views.xml',
        'views/branch_inherit_views.xml',
        'views/student_inherit_views.xml',
        'views/fee_collection_views.xml',
        'reports/transaction_report_views.xml',
        'reports/fee_collection_report_views.xml',
        'reports/transaction_voucher_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'institute_accounting/static/src/scss/dashboard.scss',
            'institute_accounting/static/src/xml/dashboard.xml',
            'institute_accounting/static/src/js/dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
