# -*- coding: utf-8 -*-
{
    'name': 'KA Tanaman',
    'version': '18.0.1.0',
    'category': 'Agriculture',
    'summary': 'Modul Master Data Tanaman: Wilayah, KUD, dan Petani',
    'author': 'PDE KBA',
    'depends': ['base', 'mail', 'ka_user_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/ka_wilayah_views.xml',
        'views/ka_kud_views.xml',
        'views/ka_petani_views.xml',
        'views/ka_tanaman_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
