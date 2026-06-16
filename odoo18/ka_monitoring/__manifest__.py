# -*- coding: utf-8 -*-
{
    'name': 'KA Monitoring Giling',
    'version': '18.0.4.0',
    'category': 'Manufacturing',
    'summary': 'Monitoring Giling & SBH PG Kebon Agung — Laporan Harian, SBH/SPT, Dashboard',
    'description': """
        Modul KA Monitoring Giling — LENGKAP (9 model).

        Konfigurasi : Musim Giling, Periode Tutupan, Harga & Biaya, Parameter.
        Input Harian: Laporan Harian Giling (tebu otomatis dari ka_timbangan,
                      jendela hari giling 06:00-06:00 WIB) + Analisa Lab.
        Monitoring  : Monitoring SBH, Monitoring SPT (read-only),
                      Rekap & Dashboard (grafik tebu/rendemen/kapasitas & laba/rugi).
    """,
    'author': 'PDE KBA',
    'depends': [
        'base',
        'mail',
        'ka_user_management',
        'ka_tanaman',
        'ka_sita',
        'ka_timbangan',
    ],
    'data': [
        # Security
        'security/ka_monitoring_groups.xml',
        'security/ir.model.access.csv',
        'security/ka_monitoring_company_rules.xml',
        # Views — Input Harian
        'views/ka_giling_harian_views.xml',
        'views/ka_giling_analisa_views.xml',
        # Views — Monitoring (read-only)
        'views/ka_giling_monitoring_sbh_views.xml',
        'views/ka_giling_monitoring_spt_views.xml',
        'views/ka_giling_rekap_views.xml',
        # Views — Konfigurasi
        'views/ka_giling_season_views.xml',
        'views/ka_giling_periode_views.xml',
        'views/ka_giling_harga_biaya_views.xml',
        'views/ka_giling_parameter_views.xml',
        # Menu (terakhir)
        'views/ka_monitoring_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
