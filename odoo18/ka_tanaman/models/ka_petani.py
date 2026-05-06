# -*- coding: utf-8 -*-
from odoo import models, fields, api


class KaPetani(models.Model):
    _name = 'ka.petani'
    _description = 'Data Petani'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'nama'
    _order = 'kode_akun'

    # ── Identitas ──────────────────────────────────────────────
    kode_akun = fields.Char(
        string='Kode Akun', required=True, tracking=True
    )
    nama = fields.Char(
        string='Nama Petani', required=True, tracking=True
    )
    no_ktp = fields.Char(
        string='No. KTP', size=16, tracking=True
    )
    nomor_hp = fields.Char(
        string='Nomor HP', tracking=True
    )

    # ── Rekening ───────────────────────────────────────────────
    no_rekening = fields.Char(
        string='No. Rekening', tracking=True
    )
    nama_rekening = fields.Char(
        string='Nama Rekening', tracking=True
    )
    nama_bank = fields.Char(
        string='Nama Bank', tracking=True
    )

    # ── Jumlah Register ────────────────────────────────────────
    # Didefinisikan sebagai integer biasa agar ka_tanaman tidak
    # bergantung pada ka_sita. Modul ka_sita akan meng-override
    # field ini menjadi computed via _inherit.
    jumlah_register = fields.Integer(
        string='Jumlah Register',
        default=0,
        readonly=True,
        help="Terisi otomatis dari modul KA SITA"
    )

    # ── PPL PIC ────────────────────────────────────────────────
    ppl_id = fields.Many2one(
        'ka.user.profile',
        string='PPL (PIC)',
        domain="[('role', '=', 'ppl')]",
        tracking=True,
        ondelete='set null'
    )

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('kode_akun_uniq', 'UNIQUE(kode_akun)', 'Kode Akun Petani harus unik!'),
        ('no_ktp_uniq', 'UNIQUE(no_ktp)', 'No. KTP Petani harus unik!'),
    ]

    def name_get(self):
        return [(r.id, f"[{r.kode_akun}] {r.nama}") for r in self]
