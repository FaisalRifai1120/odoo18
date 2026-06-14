# -*- coding: utf-8 -*-
{
    'name': 'KA SITA',
    'version': '18.0.2.0',
    'category': 'Agriculture',
    'summary': 'Sistem Informasi Tebang dan Angkut',
    'description': """
        Modul KA SITA mencakup:
        - Register (TR/TS, SBH/SPT, Harian/Periode)
        - SPTA (Surat Perintah Tebang Angkut)
        - Quota SPTA harian dengan alur persetujuan
        - Master MBS dan Jenis Truk
        - Sinkronisasi otomatis dari database PostgreSQL
    """,
    'author': 'PDE KBA',
    'depends': ['base', 'mail', 'ka_user_management', 'ka_tanaman'],
    'data': [
        'security/ir.model.access.csv',
        'security/ka_sita_record_rules.xml',
        'security/ka_sita_company_rules.xml',
        'data/ka_sync_cron.xml',
        'data/ka_spta_data.xml',
        'views/ka_register_views.xml',
        'views/ka_mbs_views.xml',
        'views/ka_jenis_truk_views.xml',
        'views/ka_quota_spta_views.xml',
        'views/ka_spta_views.xml',
        'views/ka_spta_nomor_views.xml',
        'views/ka_relaksasi_views.xml',
        'views/ka_ketentuan_views.xml',
        'views/ka_ntp_views.xml',
        'views/ka_sync_config_views.xml',
        'views/ka_sita_menu.xml',
    ],
    'external_dependencies': {
        'python': ['psycopg2', 'openpyxl'],
    },
    'assets': {
        'web.assets_backend': [
            'ka_sita/static/src/css/ntp_chatter.css',
            'ka_sita/static/src/js/ntp_chatter_toggle.js',
            'ka_sita/static/src/js/ntp_chatter_toggle.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
