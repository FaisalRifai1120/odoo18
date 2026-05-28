# -*- coding: utf-8 -*-
from odoo import models, fields, api


class KaTimbangTebu(models.Model):
    _name = 'ka.timbang.tebu'
    _description = 'Data Timbang Tebu'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'spta_id'
    _order = 'date_out DESC, spta_id'

    # ── Identitas ──────────────────────────────────────────────
    spta_id = fields.Char(string='Nomor Timbangan', required=True, tracking=True)
    no_spta = fields.Char(string='No. SPTA', tracking=True)
    kd_antrian = fields.Char(string='Nomor Antrian', tracking=True)

    # ── Register & Petani (Many2one biasa, diisi saat sync) ────
    register = fields.Char(string='Kode Register', tracking=True)
    register_id = fields.Many2one(
        'ka.sita.register', string='Register',
        ondelete='set null', tracking=True
    )
    petani_id = fields.Many2one(
        'ka.petani', string='Petani',
        ondelete='set null', tracking=True
    )

    # ── Kendaraan ──────────────────────────────────────────────
    truck_id = fields.Char(string='No. Polisi', tracking=True)

    # ── Berat ──────────────────────────────────────────────────
    weight_in = fields.Float(string='Masuk (Kg)', digits=(10, 2), tracking=True)
    weight_out = fields.Float(string='Keluar (Kg)', digits=(10, 2), tracking=True)
    weight_net = fields.Float(string='Netto (Kg)', digits=(10, 2), tracking=True)
    weight_kw = fields.Float(string='Netto (Kw)', digits=(10, 4), tracking=True)
    rafaksi = fields.Float(string='Rafaksi', digits=(10, 2), tracking=True)
    bobot_tebu = fields.Float(string='Bobot Tebu', digits=(10, 4), tracking=True)

    # ── MBS (Many2one biasa, diisi saat sync) ──────────────────
    mbs_kode = fields.Integer(string='Kode MBS', tracking=True)
    mbs_id = fields.Many2one(
        'ka.mbs', string='MBS',
        ondelete='set null', tracking=True
    )

    # ── Tanggal ────────────────────────────────────────────────
    date_in = fields.Datetime(string='Tgl. Masuk', tracking=True)
    date_out = fields.Datetime(string='Tgl. Keluar', tracking=True)

    # ── Info Tambahan ──────────────────────────────────────────
    petak = fields.Char(string='Petak', tracking=True)
    varietas = fields.Char(string='Varietas', tracking=True)
    jenis_tebu = fields.Char(string='Jenis Tebu', tracking=True)
    bobot_tebu_raw = fields.Float(string='Bobot Tebu (Raw)', digits=(10, 2), tracking=True)
    state = fields.Char(string='Status', tracking=True)

    # ── Sync key ───────────────────────────────────────────────
    sync_key = fields.Char(
        string='Sync Key', index=True,
        help='Kombinasi spta_id + truck_id sebagai key unik sync'
    )

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('sync_key_uniq', 'UNIQUE(sync_key)', 'Sync key harus unik!'),
    ]

    def name_get(self):
        return [(r.id, f"{r.spta_id} - {r.truck_id or '-'}") for r in self]
