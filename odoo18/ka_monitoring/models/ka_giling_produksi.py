# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

# ════════════════════════════════════════════════════════════════════
#  Peta Produk Produksi  →  field sumber di ka.giling.harian
#  (key, field_harian, label, kategori, sequence)
#  RS Diolah In (rs_in) SENGAJA tidak dimasukkan: itu INPUT yang diolah,
#  bukan keluaran produksi — agar Total Produksi pada pivot tidak bias.
# ════════════════════════════════════════════════════════════════════
PRODUKSI_MAP = [
    ('gkp',         'prod_gkp',    'Produksi GKP',       'gula',           10),
    ('gkp_premium', 'gkp_premium', 'GKP-Premium',        'gula',           20),
    ('gula_reject', 'gula_reject', 'Gula Reject',        'gula',           30),
    ('gula_ex2025', 'gula_ex2025', 'Gula @50kg ex-2025', 'gula',           40),
    ('produk_rs',   'produk_rs',   'Produk RS',          'rs_tetes_ampas', 50),
    ('tetes',       'tetes_ton',   'Tetes',              'rs_tetes_ampas', 60),
    ('ampas',       'ampas',       'Produksi Ampas',     'rs_tetes_ampas', 70),
]
KEY_TO_FIELD = {k: f for k, f, _l, _kat, _seq in PRODUKSI_MAP}


class KaGilingProduksi(models.Model):
    """Rincian Produksi Harian — satu baris per jenis keluaran (GKP, GKP-Premium,
    Gula Reject, Gula ex-2025, Produk RS, Tetes, Ampas) untuk satu hari giling.

    Baris DI-GENERATE otomatis dari field Produksi pada Laporan Harian Giling
    (ka.giling.harian), namun qty MASIH BISA DIKOREKSI manual. Setiap perubahan
    qty dicatat di chatter (tracking) DAN disinkronkan dua arah ke field induk
    sehingga Total Produksi / %Tetes / monitoring SBH-SPT tetap konsisten.
    """
    _name = 'ka.giling.produksi'
    _description = 'Rincian Produksi Harian'
    _inherit = ['mail.thread']
    _rec_name = 'display_name'
    _order = 'giling_id, sequence, id'

    giling_id = fields.Many2one(
        'ka.giling.harian', string='Hari Giling', required=True,
        ondelete='cascade', index=True
    )
    company_id = fields.Many2one(
        'res.company', string='Unit',
        related='giling_id.company_id', store=True, readonly=True
    )
    date = fields.Date(string='Tanggal', related='giling_id.date', store=True, readonly=True)
    gil_ke = fields.Integer(string='Giling ke-', related='giling_id.gil_ke', store=True, readonly=True)
    season_id = fields.Many2one(
        'ka.giling.season', string='Musim',
        related='giling_id.season_id', store=True, readonly=True
    )
    periode_id = fields.Many2one(
        'ka.giling.periode', string='Periode',
        related='giling_id.periode_id', store=True, readonly=True
    )

    product_key = fields.Selection(
        [(k, l) for k, _f, l, _kat, _seq in PRODUKSI_MAP],
        string='Produk', required=True, index=True)
    name = fields.Char(string='Keterangan')
    kategori = fields.Selection(
        [('gula', 'Gula'), ('rs_tetes_ampas', 'RS, Tetes & Ampas')],
        string='Kategori', index=True)
    sequence = fields.Integer(string='Urutan', default=10)
    uom_name = fields.Char(string='Satuan', default='Ton', readonly=True)

    # qty: diisi otomatis dari induk, dapat dikoreksi manual, perubahan dilacak
    qty = fields.Float(string='Jumlah (Ton)', digits=(16, 3), tracking=True)
    # % terhadap total tebu tergiling hari itu
    pct_tebu = fields.Float(string='% Tebu', digits=(8, 4),
                            compute='_compute_pct_tebu', store=True)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('uniq_giling_product',
         'unique(giling_id, product_key)',
         'Tiap jenis produk hanya boleh satu baris per hari giling.'),
    ]

    @api.depends('qty', 'giling_id.tebu_total')
    def _compute_pct_tebu(self):
        for rec in self:
            tebu = rec.giling_id.tebu_total or 0.0
            rec.pct_tebu = (100.0 * rec.qty / tebu) if tebu else 0.0

    @api.depends('name', 'date', 'qty')
    def _compute_display_name(self):
        for rec in self:
            tgl = fields.Date.to_string(rec.date) if rec.date else ''
            rec.display_name = f"{rec.name or rec.product_key} — {tgl}" if tgl else (rec.name or rec.product_key or '')

    # ── Sinkron dua arah: koreksi baris → tulis balik ke field induk ──
    def write(self, vals):
        res = super().write(vals)
        if 'qty' in vals and not self.env.context.get('skip_giling_sync'):
            for line in self:
                fname = KEY_TO_FIELD.get(line.product_key)
                if fname and line.giling_id:
                    if (line.giling_id[fname] or 0.0) != (line.qty or 0.0):
                        line.giling_id.with_context(skip_produksi_sync=True).write({fname: line.qty})
        return res
