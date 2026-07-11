# -*- coding: utf-8 -*-
{
    'name': 'KA Cetak NGP',
    'version': '18.0.1.0.0',
    'category': 'Agriculture',
    'summary': 'Cetak Surat Penyerahan Gula (NGP) dari Excel, dengan validasi Register ka_sita',
    'description': """
        Modul bantu cetak NGP (Nota Gula Petani):
        - Import data dari Excel (menggantikan mail-merge Word manual)
        - Validasi Nomor Register terhadap ka_sita.register
        - Cetak PDF A4 berisi 2 NGP (A5) per halaman, dengan QR Code inline (SVG)
    """,
    'author': 'PDE KBA',
    'depends': ['base', 'mail', 'ka_user_management', 'ka_sita'],
    'external_dependencies': {'python': ['openpyxl', 'qrcode']},
    'data': [
        'security/ka_cetak_security.xml',
        'security/ir.model.access.csv',
        'security/ka_cetak_company_rules.xml',
        'report/ka_cetak_ngp_report.xml',
        'views/ka_cetak_ngp_views.xml',
        'views/ka_cetak_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'ka_cetak/static/src/js/print_progress.js',
            'ka_cetak/static/src/xml/print_progress.xml',
        ],
    },
}
