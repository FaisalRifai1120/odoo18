# -*- coding: utf-8 -*-
from odoo import models, fields, api


class KaSitaRegister(models.Model):
    _name = 'ka.sita.register'
    _description = 'Register SITA'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'nama_register'
    _order = 'kode_register'

    # ── Identitas Register ─────────────────────────────────────
    kode_register = fields.Char(
        string='Kode Register', required=True, tracking=True
    )
    nama_register = fields.Char(
        string='Nama Register', required=True, tracking=True
    )
    jenis_register = fields.Selection([
        ('TR', 'TR (Tebu Rakyat)'),
        ('TS', 'TS (Tebu Sendiri)'),
    ], string='Jenis Register', required=True, tracking=True)

    metode = fields.Selection([
        ('SBH', 'SBH (Sistem Bagi Hasil)'),
        ('SPT', 'SPT (Sewa Per Ton)'),
    ], string='Metode', required=True, tracking=True)

    jenis_pembayaran = fields.Selection([
        ('Harian',  'Harian'),
        ('Periode', 'Periode'),
    ], string='Jenis Pembayaran', required=True, tracking=True)

    # ── KUD & Wilayah ──────────────────────────────────────────
    kud_id = fields.Many2one(
        'ka.kud', string='KUD', required=False,
        ondelete='restrict', tracking=True
    )
    desa_id = fields.Many2one(
        'ka.wilayah.desa', string='Desa',
        ondelete='restrict', tracking=True
    )
    kecamatan_id = fields.Many2one(
        'ka.wilayah.kecamatan', string='Kecamatan',
        ondelete='restrict', tracking=True
    )

    # ── Petani ─────────────────────────────────────────────────
    petani_id = fields.Many2one(
        'ka.petani', string='Petani',
        ondelete='restrict', tracking=True
    )
    account_petani_id = fields.Many2one(
        'ka.petani', string='Account Petani',
        ondelete='restrict', tracking=True,
        help="Pilih petani berdasarkan Kode Akun - Nama"
    )

    # ── Transfer & Rekening ────────────────────────────────────
    is_transfer = fields.Boolean(
        string='Transfer', default=False, tracking=True
    )
    no_rekening = fields.Char(
        string='No. Rekening', tracking=True
    )
    nama_bank = fields.Char(
        string='Nama Bank', tracking=True
    )
    nama_rekening = fields.Char(
        string='Nama Rekening', tracking=True
    )
    no_ktp = fields.Char(
        string='Nomor KTP', size=16, tracking=True
    )

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('kode_register_uniq', 'UNIQUE(kode_register)',
         'Kode Register harus unik!'),
    ]

    # ── Onchange: isi otomatis dari petani ────────────────────
    @api.onchange('petani_id')
    def _onchange_petani_id(self):
        if self.petani_id:
            p = self.petani_id
            self.no_rekening   = p.no_rekening   or self.no_rekening
            self.nama_bank     = p.nama_bank     or self.nama_bank
            self.nama_rekening = p.nama_rekening or self.nama_rekening
            self.no_ktp        = p.no_ktp        or self.no_ktp
            self.account_petani_id = p.id

    @api.onchange('account_petani_id')
    def _onchange_account_petani_id(self):
        if self.account_petani_id:
            p = self.account_petani_id
            self.no_rekening   = p.no_rekening   or self.no_rekening
            self.nama_bank     = p.nama_bank     or self.nama_bank
            self.nama_rekening = p.nama_rekening or self.nama_rekening
            if not self.petani_id:
                self.petani_id = p.id

    @api.onchange('desa_id')
    def _onchange_desa_id(self):
        if self.desa_id:
            self.kecamatan_id = self.desa_id.kecamatan_id

    def name_get(self):
        return [(r.id, f"[{r.kode_register}] {r.nama_register}") for r in self]

    # ── Update jumlah_register di petani saat create/unlink ───
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_petani_jumlah_register()
        return records

    def unlink(self):
        petani_ids = self.mapped('petani_id')
        res = super().unlink()
        petani_ids._recompute_jumlah_register()
        return res

    def _update_petani_jumlah_register(self):
        for rec in self:
            if rec.petani_id:
                rec.petani_id._recompute_jumlah_register()


class KaPetaniInherit(models.Model):
    """Extend ka.petani dari modul ka_sita untuk mengelola jumlah_register."""
    _inherit = 'ka.petani'

    register_ids = fields.One2many(
        'ka.sita.register', 'petani_id',
        string='Daftar Register'
    )

    def _recompute_jumlah_register(self):
        for rec in self:
            rec.jumlah_register = self.env['ka.sita.register'].search_count(
                [('petani_id', '=', rec.id)]
            )
