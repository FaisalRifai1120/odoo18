# -*- coding: utf-8 -*-
from odoo import models, fields


class KaAnalisaQc(models.Model):
    """Data Analisa QC dari PostgreSQL table data_analisa_qc."""
    _name = 'ka.analisa.qc'
    _description = 'Analisa QC Tebu'
    _rec_name = 'no_spta'
    _order = 'created_at DESC'

    # ── Identitas ──────────────────────────────────────────────
    no_spta     = fields.Char(string='No. SPTA', required=True, index=True)
    kd_antrian  = fields.Char(string='Kode Antrian', index=True)

    # ── Relasi ke timbang ──────────────────────────────────────
    timbang_id  = fields.Many2one(
        'ka.timbang.tebu', string='Data Timbang',
        ondelete='set null', readonly=True,
        help='Link ke data timbang via kd_antrian'
    )

    # ── Brix & Pol Core ────────────────────────────────────────
    pos_brix        = fields.Float(string='Pos Brix', digits=(10, 4))
    varietas_brix   = fields.Char(string='Varietas Brix')
    brix_core       = fields.Float(string='Brix Core', digits=(10, 4))
    pol_core        = fields.Float(string='Pol Core', digits=(10, 4))
    rend_core       = fields.Float(string='Rendemen Core', digits=(10, 4))

    # ── Brix & Pol Ari ─────────────────────────────────────────
    brix_ari        = fields.Float(string='Brix Ari', digits=(10, 4))
    pol_ari         = fields.Float(string='Pol Ari', digits=(10, 4))
    rend_ari        = fields.Float(string='Rendemen Ari', digits=(10, 4))

    # ── Rendemen ───────────────────────────────────────────────
    rend_npp        = fields.Float(string='Rendemen NPP', digits=(10, 4))
    rend_perjam     = fields.Float(string='Rendemen Per Jam', digits=(10, 4))
    rend_harian     = fields.Float(string='Rendemen Harian', digits=(10, 4))

    # ── Timestamp ──────────────────────────────────────────────
    created_at  = fields.Datetime(string='Dibuat', readonly=True)
    updated_at  = fields.Datetime(string='Diperbarui', readonly=True)

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('no_spta_uniq', 'UNIQUE(no_spta)', 'No. SPTA QC harus unik!'),
    ]
