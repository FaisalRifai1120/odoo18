# -*- coding: utf-8 -*-
{
    'name': 'KA SITA',
    'version': '18.0.1.0',
    'category': 'Agriculture',
    'summary': 'Modul SITA: Sistem Informasi Tanaman - Register',
    'description': """
        Modul KA SITA mencakup:
        - Register (TR/TS, SBH/SPT, Harian/Periode)
        - Master MBS (Masakan Brix Standar)
        - Integrasi dengan Petani, KUD, Wilayah dari modul KA Tanaman
        - Sinkronisasi otomatis dari database PostgreSQL eksternal
    """,
    'author': 'PDE KBA',
    'depends': ['base', 'mail', 'ka_user_management', 'ka_tanaman'],
    'data': [
        'security/ir.model.access.csv',
        'security/ka_sita_record_rules.xml',
        'data/ka_sync_cron.xml',
        'views/ka_register_views.xml',
        'views/ka_mbs_views.xml',
        'views/ka_sync_config_views.xml',
        'views/ka_sita_menu.xml',
    ],
    'external_dependencies': {
        'python': ['psycopg2'],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
