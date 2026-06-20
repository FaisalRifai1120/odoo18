# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaKasbankInventory(models.Model):
    """Persediaan Gula harian per produk & tahun produksi (sheet Gula Eks 2025/2026).

    saldo_akhir = saldo_awal + produksi − penjualan.
    Saldo BOLEH negatif (oversold/carry-over) → tidak diblok, hanya ditandai
    anomali (baris merah) agar mudah ditinjau.
    """
    _name = 'ka.kasbank.inventory'
    _description = 'Persediaan Gula'
    _inherit = ['mail.thread']
    _rec_name = 'display_name'
    _order = 'date desc, product_id'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company)
    date = fields.Date(string='Tanggal', required=True, index=True,
                       default=fields.Date.context_today)
    product_id = fields.Many2one('ka.kasbank.product', string='Produk', required=True, index=True)
    production_year = fields.Integer(
        string='Eks Produksi (Tahun)', index=True,
        default=lambda self: fields.Date.context_today(self).year,
        help='Tahun produksi gula (Eks Produksi), mis. 2025 / 2026.')

    saldo_awal = fields.Float(string='Saldo Awal (Ton)', digits=(16, 3), tracking=True)
    produksi = fields.Float(string='Produksi / Diolah (Ton)', digits=(16, 3), tracking=True)
    penjualan = fields.Float(string='Penjualan (Ton)', digits=(16, 3), tracking=True)
    saldo_akhir = fields.Float(string='Saldo Akhir (Ton)', digits=(16, 3),
                               compute='_compute_saldo_akhir', store=True)
    is_anomaly = fields.Boolean(string='Anomali (saldo < 0)',
                                compute='_compute_saldo_akhir', store=True)
    note = fields.Char(string='Keterangan')

    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('uniq_inventory', 'unique(date, company_id, product_id, production_year)',
         'Persediaan untuk tanggal, unit, produk & tahun produksi ini sudah ada.'),
    ]

    @api.depends('saldo_awal', 'produksi', 'penjualan')
    def _compute_saldo_akhir(self):
        for rec in self:
            rec.saldo_akhir = (rec.saldo_awal or 0.0) + (rec.produksi or 0.0) - (rec.penjualan or 0.0)
            rec.is_anomaly = rec.saldo_akhir < 0

    @api.depends('product_id', 'production_year', 'date')
    def _compute_display_name(self):
        for rec in self:
            prod = rec.product_id.name or ''
            tgl = fields.Date.to_string(rec.date) if rec.date else ''
            rec.display_name = f"{prod} ({rec.production_year}) · {tgl}".strip()
