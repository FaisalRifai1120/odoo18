# -*- coding: utf-8 -*-
{
    'name': 'KA SITA',
    'version': '18.0.1.0',
    'category': 'Agriculture',
    'summary': 'Modul SITA: Sistem Informasi Tanaman - Register',
    'description': """
        Modul KA SITA mencakup:
        - Register (TR/TS, SBH/SPT, Harian/Periode)
        - Integrasi dengan Petani, KUD, Wilayah dari modul KA Tanaman
    """,
    'author': 'PDE KBA',
    'depends': ['base', 'mail', 'ka_user_management', 'ka_tanaman'],
    'data': [
        'security/ir.model.access.csv',
        'security/ka_sita_record_rules.xml',
        'views/ka_register_views.xml',
        'views/ka_sita_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
