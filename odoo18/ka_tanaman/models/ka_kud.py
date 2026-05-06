# -*- coding: utf-8 -*-
from odoo import models, fields


class KaKud(models.Model):
    _name = 'ka.kud'
    _description = 'KUD (Koperasi Unit Desa)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'nama'
    _order = 'kode'

    kode = fields.Char(
        string='Kode KUD', required=True, size=20, tracking=True
    )
    nama = fields.Char(
        string='Nama KUD', required=True, tracking=True
    )

    # ── Alamat ─────────────────────────────────────────────────
    kota_id = fields.Many2one(
        'ka.wilayah.kota', string='Kota/Kabupaten',
        required=True, tracking=True, ondelete='restrict'
    )
    provinsi_id = fields.Many2one(
        'ka.wilayah.provinsi', related='kota_id.provinsi_id',
        store=True, readonly=True, string='Provinsi'
    )
    kota_nama = fields.Char(
        string='Nama Kota (bebas)', tracking=True,
        help="Isi jika nama kota berbeda dengan pilihan di tabel wilayah"
    )
    alamat = fields.Text(string='Alamat Lengkap', tracking=True)
    no_telepon = fields.Char(string='No. Telepon', tracking=True)

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('kode_uniq', 'UNIQUE(kode)', 'Kode KUD harus unik!'),
    ]

    def name_get(self):
        return [(r.id, f"[{r.kode}] {r.nama}") for r in self]
