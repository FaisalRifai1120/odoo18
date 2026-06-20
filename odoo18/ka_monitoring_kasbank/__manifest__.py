# -*- coding: utf-8 -*-
{
    'name': 'KA Monitoring Kas/Bank & Persediaan',
    'version': '18.0.6.0.0',
    'category': 'Accounting/Inventory',
    'summary': 'Monitoring Kas/Bank, Deposito, Hutang, Persediaan & Penjualan Gula PG Kebon Agung',
    'description': """
        KA Monitoring Kas/Bank & Persediaan — dibangun bertahap.

        FASE 1 (modul ini): Fondasi & Master Data
            - Master Akun Kas/Bank (ka.kasbank.account)
            - Master Produk Gula  (ka.kasbank.product)
            - Keamanan: kategori & grup tersendiri (Pengguna / Manajer)

        Roadmap berikutnya:
            FASE 2 — Saldo Kas/Bank harian, Deposito, Hutang Bank
            FASE 3 — Persediaan gula, Penjualan Bulk & Ritel
            FASE 4 — Wizard Import dari Excel
            FASE 5 — Dashboard KPI & tarik data dari ka_monitoring
    """,
    'author': 'PDE KBA',
    'depends': [
        'base',
        'mail',
        'ka_monitoring',  # Fase 5b: tarik produksi giling → persediaan
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'data': [
        # Security
        'security/ka_kasbank_security.xml',
        'security/ir.model.access.csv',
        'security/ka_kasbank_company_rules.xml',
        # Views — Master
        'views/ka_kasbank_account_views.xml',
        'views/ka_kasbank_product_views.xml',
        # Views — Kas & Bank (Fase 2)
        'views/ka_kasbank_balance_views.xml',
        'views/ka_kasbank_deposito_views.xml',
        'views/ka_kasbank_loan_views.xml',
        # Views — Persediaan & Penjualan (Fase 3)
        'views/ka_kasbank_inventory_views.xml',
        'views/ka_kasbank_sales_bulk_views.xml',
        'views/ka_kasbank_sales_retail_views.xml',
        # Wizard Import (Fase 4)
        'wizard/ka_kasbank_import_wizard_views.xml',
        # Wizard Tarik Produksi (Fase 5b)
        'wizard/ka_kasbank_produksi_pull_views.xml',
        # Dashboard (Fase 5)
        'views/ka_kasbank_dashboard_views.xml',
        # Menu (terakhir)
        'views/ka_kasbank_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
