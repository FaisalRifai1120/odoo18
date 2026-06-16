# -*- coding: utf-8 -*-
{
    'name': 'KA Monitoring Giling',
    'version': '18.0.3.1',
    'category': 'Manufacturing',
    'summary': 'Monitoring Giling & SBH PG Kebon Agung — Laporan Harian, SBH/SPT, Dashboard',
    'description': """
        Modul KA Monitoring Giling.

        FASE 1: Musim Giling.
        FASE 2: Konfigurasi (Periode, Harga & Biaya, Parameter).
        FASE 3 (aktif): Laporan Harian Giling — tebu otomatis dari ka_timbangan
                        + perhitungan Monitoring SBH/SPT.
        Fase berikutnya: Analisa Lab, view Monitoring SBH/SPT, Rekap & Dashboard.
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
