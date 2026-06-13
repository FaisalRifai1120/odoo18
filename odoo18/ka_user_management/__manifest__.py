# -*- coding: utf-8 -*-
{
    'name': 'KA User Management',
    'version': '18.0.2.0',
    'category': 'Administration',
    'summary': 'Manajemen User berdasarkan Struktur Organisasi',
    'author': 'PDE KBA',
    'depends': ['base', 'mail'],
    'data': [
        'security/ka_user_groups.xml',
        'security/ka_user_company_rules.xml',
        'security/ir.model.access.csv',
        'views/ka_user_views.xml',
        'views/ka_user_menu.xml',
        'data/ka_user_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
