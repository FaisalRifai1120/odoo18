# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaGilingAnalisa(models.Model):
    """Analisa Lab Harian (DT_HARIAN) — 1 record per hari giling, terhubung ke ka.giling.harian."""
    _name = 'ka.giling.analisa'
    _description = 'Analisa Lab Harian'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'giling_id'
    _order = 'date DESC'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company',
        related='giling_id.company_id', store=True, readonly=True
    )
    giling_id = fields.Many2one(
        'ka.giling.harian', string='Hari Giling', required=True,
        ondelete='cascade', index=True
    )
    date = fields.Date(string='Tanggal', related='giling_id.date', store=True, readonly=True)
    gil_ke = fields.Integer(string='Giling ke-', related='giling_id.gil_ke', store=True, readonly=True)

    # ── Nira ───────────────────────────────────────────────────
    nm_pct = fields.Float(string='NM (%)', digits=(8, 2))
    imb_pct = fields.Float(string='IMB (%)', digits=(8, 2))
    npp_brix = fields.Float(string='NPP Brix (%)', digits=(8, 2))
    npp_pol = fields.Float(string='NPP Pol (%)', digits=(8, 2))
    nm_brix = fields.Float(string='Nira Mentah Brix (%)', digits=(8, 2))
    nm_pol = fields.Float(string='Nira Mentah Pol (%)', digits=(8, 2))
    rend_npp = fields.Float(string='Rendemen NPP (FR 0.7) (%)', digits=(8, 4))
    rend_nm = fields.Float(string='Rendemen NM (WR 97) (%)', digits=(8, 4))

    # ── ICUMSA ─────────────────────────────────────────────────
    icumsa_p1 = fields.Float(string='ICUMSA P1 (IU)', digits=(10, 2), help='max. 100 IU')
    icumsa_p2 = fields.Float(string='ICUMSA P2 (IU)', digits=(10, 2), help='max. 150 IU')
    icumsa_gkp = fields.Float(string='ICUMSA GKP (IU)', digits=(10, 2), help='max. 300 IU')
    icumsa_rs = fields.Float(string='ICUMSA Produk RS (IU)', digits=(10, 2))

    # ── Kadar SO2 ──────────────────────────────────────────────
    so2_p1 = fields.Float(string='SO2 P1 (ppm)', digits=(8, 2), help='max. 2 ppm')
    so2_p2 = fields.Float(string='SO2 P2 (ppm)', digits=(8, 2), help='max. 5 ppm')
    so2_gkp = fields.Float(string='SO2 GKP (ppm)', digits=(8, 2), help='max. 15 ppm')

    # ── Bahan Baku Tebu ────────────────────────────────────────
    bbt_pol = fields.Float(string='BBT Pol (%)', digits=(8, 2))
    bbt_brix = fields.Float(string='BBT Brix (%)', digits=(8, 2))
    bbt_sabut = fields.Float(string='BBT Sabut (%)', digits=(8, 2))
    bbt_knt = fields.Float(string='Nira Tebu (KNT) (%)', digits=(8, 2))
    bbt_brix_pucuk = fields.Float(string='Brix Pucuk (%)', digits=(8, 2))

    # ── Kinerja Gilingan ───────────────────────────────────────
    hpb1 = fields.Float(string='HPB 1 (%)', digits=(8, 2))
    hpb_total = fields.Float(string='HPB Total (%)', digits=(8, 2))
    pshk = fields.Float(string='PSHK (%)', digits=(8, 2))
    hpg = fields.Float(string='HPG (%)', digits=(8, 2))
    pol_ampas = fields.Float(string='Pol Ampas (%)', digits=(8, 2))
    zk_ampas = fields.Float(string='ZK Ampas (%)', digits=(8, 2))

    # ── Kinerja Proses ─────────────────────────────────────────
    delta_hk = fields.Float(string='Delta HK (Ne-Nm)', digits=(8, 2))
    angka_pemurnian = fields.Float(string='Angka Pemurnian', digits=(8, 2))
    pol_blotong = fields.Float(string='Pol Blotong (%)', digits=(8, 2))
    bhr = fields.Float(string='BHR (%)', digits=(8, 2))
    wr = fields.Float(string='WR (%)', digits=(8, 2))

    # ── Kristal Dalam Proses ───────────────────────────────────
    kristal_total = fields.Float(string='Kristal Total (Ton)', digits=(12, 3))
    kristal_tebu = fields.Float(string='Kristal Tebu (Ton)', digits=(12, 3))
    kristal_rs = fields.Float(string='Kristal RS (Ton)', digits=(12, 3))
    hk_tetes = fields.Float(string='HK Tetes (%)', digits=(8, 2))

    # ── Computed (turunan dari giling/lab) ─────────────────────
    listrik_per_tebu = fields.Float(string='Listrik per Tebu (KWH/Ton)', digits=(12, 4),
                                    compute='_compute_derived', store=True)
    uap_pct_tebu = fields.Float(string='Konsumsi Uap % Tebu (%)', digits=(8, 4),
                                compute='_compute_derived', store=True)
    fr_calc = fields.Float(string='Faktor Rendemen (FR) (%)', digits=(10, 4),
                           compute='_compute_derived', store=True,
                           help='= (KNT × HPB Total × PSHK × WR) / 1e8')
    or_recovery = fields.Float(string='Overall Recovery (OR) (%)', digits=(10, 4),
                               compute='_compute_derived', store=True,
                               help='= (HPG × BHR) / 100')
    potensi_kehilangan_ton = fields.Float(string='Potensi Kehilangan Gula ke Tetes (Ton)', digits=(12, 4),
                                          compute='_compute_derived', store=True)
    potensi_kehilangan_rp = fields.Float(string='Potensi Kehilangan Gula (Rp)', digits=(18, 2),
                                         compute='_compute_derived', store=True)

    notes = fields.Text(string='Catatan')

    _sql_constraints = [
        ('giling_uniq', 'UNIQUE(giling_id)',
         'Setiap hari giling hanya boleh punya satu record Analisa Lab!'),
    ]

    @api.depends('giling_id.listrik_pg', 'giling_id.listrik_pln', 'giling_id.tebu_total',
                 'giling_id.prod_uap', 'giling_id.pct_tetes',
                 'bbt_knt', 'hpb_total', 'pshk', 'wr', 'hpg', 'bhr')
    def _compute_derived(self):
        for rec in self:
            g = rec.giling_id
            tebu = g.tebu_total if g else 0.0
            # listrik per tebu
            rec.listrik_per_tebu = (
                ((g.listrik_pg or 0.0) + (g.listrik_pln or 0.0)) / tebu
            ) if (g and tebu) else 0.0
            # konsumsi uap % tebu
            rec.uap_pct_tebu = (100.0 * (g.prod_uap or 0.0) / tebu) if (g and tebu) else 0.0
            # FR = (KNT × HPB_total × PSHK × WR) / 1e8
            rec.fr_calc = (
                (rec.bbt_knt or 0.0) * (rec.hpb_total or 0.0) * (rec.pshk or 0.0) * (rec.wr or 0.0)
            ) / 1e8
            # OR = (HPG × BHR) / 100
            rec.or_recovery = ((rec.hpg or 0.0) * (rec.bhr or 0.0)) / 100.0
            # Potensi kehilangan gula ke tetes (Ton) = tebu × tetes%tebu × delta_kristal / 10000
            # delta_kristal didekati dari HK tetes — disederhanakan: pakai pct_tetes sebagai proxy
            pct_tetes = g.pct_tetes if g else 0.0
            rec.potensi_kehilangan_ton = (tebu * pct_tetes * (rec.delta_hk or 0.0)) / 10000.0
            rec.potensi_kehilangan_rp = rec.potensi_kehilangan_ton * 2000000.0

    def name_get(self):
        result = []
        for rec in self:
            label = _('Analisa')
            if rec.giling_id:
                label = _('Analisa — %s') % (rec.giling_id.display_name or '')
            result.append((rec.id, label))
        return result
