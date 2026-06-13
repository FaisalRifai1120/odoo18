# -*- coding: utf-8 -*-
{
    'name': 'KA Timbangan',
    'version': '18.0.1.0',
    'category': 'Agriculture',
    'summary': 'Modul Timbangan: Data timbang tebu + Laporan',
    'description': """
        Modul KA Timbangan mencakup:
        - Data Timbang Tebu (sync dari v_spta_timb_odoo)
        - Laporan Harian, per Register, per PPL, Detail
        - Hak akses hierarki (PPL → KASUBSI → KASI → KABAG)
        - Sinkronisasi otomatis (cron) dan manual (rentang tanggal)
    """,
    'author': 'PDE KBA',
    'depends': ['base', 'mail', 'ka_user_management', 'ka_tanaman', 'ka_sita'],
    'data': [
        'security/ir.model.access.csv',
        'security/ka_timbangan_record_rules.xml',
        'data/ka_timbangan_cron.xml',
        'views/ka_tebu_views.xml',
        'views/ka_laporan_views.xml',
        'views/ka_timbangan_sync_views.xml',
        'views/ka_analisa_qc_views.xml',
        'views/ka_timbangan_menu.xml',
    ],
    'external_dependencies': {
        'python': ['psycopg2'],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
