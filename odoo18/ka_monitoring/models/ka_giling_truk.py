# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaGilingTruk(models.Model):
    """Rincian Truk Giling — satu baris per truk (record ka.timbang.tebu) yang
    membentuk angka tebu tergiling pada satu hari giling, lengkap dengan laba/rugi
    per truk. Baris ini DIGENERATE otomatis saat 'Tarik Data Timbangan'
    (bukan input manual).

    Rendemen HYBRID: pakai Rendemen QC milik truk bila terisi; bila kosong,
    pakai rendemen kategori harian (rend_tr/ts/spt) dari Laporan Harian.
    """
    _name = 'ka.giling.truk'
    _description = 'Rincian Truk Giling'
    _order = 'giling_id, kategori, no_spta'

    giling_id = fields.Many2one(
        'ka.giling.harian', string='Hari Giling', required=True,
        ondelete='cascade', index=True
    )
    company_id = fields.Many2one(
        'res.company', string='Unit',
        related='giling_id.company_id', store=True, readonly=True
    )
    date = fields.Date(string='Tanggal', related='giling_id.date', store=True, readonly=True)
    season_id = fields.Many2one(
        'ka.giling.season', string='Musim',
        related='giling_id.season_id', store=True, readonly=True
    )
    periode_id = fields.Many2one(
        'ka.giling.periode', string='Periode',
        related='giling_id.periode_id', store=True, readonly=True
    )

    # ── Identitas truk (snapshot dari ka.timbang.tebu) ─────────
    timbang_id = fields.Many2one('ka.timbang.tebu', string='Data Timbangan', ondelete='set null')
    no_spta = fields.Char(string='No. SPTA')
    register_id = fields.Many2one('ka.sita.register', string='Register', index=True)
    kategori = fields.Selection(
        [('tr_sbh', 'TR-SBH'), ('ts', 'TS'), ('spt', 'SPT')],
        string='Kategori')
    date_out = fields.Datetime(string='Jam Keluar')

    # ── Fisik (snapshot) ───────────────────────────────────────
    tebu_ton = fields.Float(string='Tebu (Ton)', digits=(16, 2))
    rend_qc = fields.Float(string='Rendemen QC (%)', digits=(8, 4),
                           help='Rendemen NPP dari Analisa QC pada data timbangan (bila ada)')

    # ── Rendemen terpakai & hasil hitung (computed) ────────────
    rend = fields.Float(string='Rendemen (%)', digits=(8, 4),
                        compute='_compute_truk_financials', store=True)
    rend_source = fields.Selection(
        [('qc', 'QC Truk'), ('harian', 'Rendemen Harian')],
        string='Sumber Rendemen', compute='_compute_truk_financials', store=True)
    prod_gula = fields.Float(string='Produksi Gula (Ton)', digits=(16, 4),
                             compute='_compute_truk_financials', store=True)
    prod_tetes = fields.Float(string='Produksi Tetes (Ton)', digits=(16, 4),
                              compute='_compute_truk_financials', store=True)
    pendapatan_ku = fields.Float(string='Pendapatan (Rp/Ku)', digits=(16, 2),
                                 compute='_compute_truk_financials', store=True)
    laba_biaya_ku = fields.Float(string='Laba thd Biaya Produksi (Rp/Ku)', digits=(16, 2),
                                 compute='_compute_truk_financials', store=True)
    laba_biaya_rp = fields.Float(string='Laba thd Biaya Produksi (Rp)', digits=(18, 2),
                                 compute='_compute_truk_financials', store=True)
    labarugi_ku = fields.Float(string='Laba/Rugi Total (Rp/Ku)', digits=(16, 2),
                               compute='_compute_truk_financials', store=True)
    labarugi_rp = fields.Float(string='Laba/Rugi Total (Rp)', digits=(18, 2),
                               compute='_compute_truk_financials', store=True)
    status = fields.Selection([('laba', 'Laba'), ('rugi', 'Rugi')],
                              string='Status', compute='_compute_truk_financials', store=True)

    @api.depends(
        'tebu_ton', 'rend_qc', 'kategori',
        'giling_id.rend_tr', 'giling_id.rend_ts', 'giling_id.rend_spt',
        'giling_id.pct_tetes', 'giling_id.faktor_gula',
        'giling_id.harga_gula', 'giling_id.harga_tetes',
        'giling_id.biaya_produksi', 'giling_id.biaya_laba',
        'giling_id.bagi_hasil_rate', 'giling_id.pembelian_spt',
    )
    def _compute_truk_financials(self):
        for line in self:
            g = line.giling_id
            faktor = (g.faktor_gula or 1.003) if g else 1.003
            pct_tetes = (g.pct_tetes or 0.0) if g else 0.0
            tebu = line.tebu_ton or 0.0

            # Rendemen HYBRID
            if line.rend_qc:
                rend = line.rend_qc
                line.rend_source = 'qc'
            else:
                rend = {
                    'tr_sbh': g.rend_tr if g else 0.0,
                    'ts': g.rend_ts if g else 0.0,
                    'spt': g.rend_spt if g else 0.0,
                }.get(line.kategori, 0.0) or 0.0
                line.rend_source = 'harian'
            line.rend = rend

            line.prod_gula = tebu * rend * faktor / 100.0
            line.prod_tetes = tebu * pct_tetes / 100.0

            harga_gula = g.harga_gula if g else 0.0
            harga_tetes = g.harga_tetes if g else 0.0

            if line.kategori == 'spt':
                # SPT — pabrik membeli tebu
                line.pendapatan_ku = (
                    (line.prod_gula * harga_gula + line.prod_tetes * harga_tetes) / tebu / 10.0 * 1000.0
                ) if tebu else 0.0
                laba_pembelian = line.pendapatan_ku - (g.pembelian_spt if g else 0.0)
                line.laba_biaya_ku = laba_pembelian - (g.biaya_produksi if g else 0.0)
                line.labarugi_ku = laba_pembelian - (g.biaya_laba if g else 0.0)
            else:
                # SBH (TR-SBH / TS) — bagi hasil ke petani
                gula_milik_pg = line.prod_gula - ((g.bagi_hasil_rate if g else 0.0) * tebu / 100.0)
                line.pendapatan_ku = (
                    (gula_milik_pg * harga_gula + line.prod_tetes * harga_tetes) / tebu / 10.0 * 1000.0
                ) if tebu else 0.0
                line.laba_biaya_ku = line.pendapatan_ku - (g.biaya_produksi if g else 0.0)
                line.labarugi_ku = line.pendapatan_ku - (g.biaya_laba if g else 0.0)

            line.laba_biaya_rp = line.laba_biaya_ku * tebu * 10.0
            line.labarugi_rp = line.labarugi_ku * tebu * 10.0
            line.status = ('laba' if line.labarugi_rp >= 0 else 'rugi') if tebu else False

    def name_get(self):
        result = []
        for rec in self:
            label = rec.no_spta or (rec.register_id.display_name if rec.register_id else _('Truk'))
            result.append((rec.id, label))
        return result
