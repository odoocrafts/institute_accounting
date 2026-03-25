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
        'views/menu_views.xml',
        'views/type_views.xml',
        'views/transaction_views.xml',
        'views/user_views.xml',
        'reports/transaction_report_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
