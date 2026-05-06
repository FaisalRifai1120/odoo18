# -*- coding: utf-8 -*-
from odoo import models, fields, api


class KaProvinsi(models.Model):
    _name = 'ka.wilayah.provinsi'
    _description = 'Provinsi'
    _rec_name = 'nama'
    _order = 'kode'

    kode = fields.Char(string='Kode Provinsi', required=True, size=10)
    nama = fields.Char(string='Nama Provinsi', required=True)
    active = fields.Boolean(default=True)

    kota_ids = fields.One2many(
        'ka.wilayah.kota', 'provinsi_id', string='Daftar Kota/Kabupaten'
    )
    kota_count = fields.Integer(
        string='Jumlah Kota', compute='_compute_kota_count'
    )

    _sql_constraints = [
        ('kode_uniq', 'UNIQUE(kode)', 'Kode Provinsi harus unik!'),
    ]

    @api.depends('kota_ids')
    def _compute_kota_count(self):
        for rec in self:
            rec.kota_count = len(rec.kota_ids)

    def name_get(self):
        return [(r.id, f"[{r.kode}] {r.nama}") for r in self]


class KaKota(models.Model):
    _name = 'ka.wilayah.kota'
    _description = 'Kota / Kabupaten'
    _rec_name = 'nama'
    _order = 'kode'

    kode = fields.Char(string='Kode Kota/Kab', required=True, size=10)
    nama = fields.Char(string='Nama Kota/Kabupaten', required=True)
    provinsi_id = fields.Many2one(
        'ka.wilayah.provinsi', string='Provinsi', required=True, ondelete='restrict'
    )
    active = fields.Boolean(default=True)

    kecamatan_ids = fields.One2many(
        'ka.wilayah.kecamatan', 'kota_id', string='Daftar Kecamatan'
    )
    kecamatan_count = fields.Integer(
        string='Jumlah Kecamatan', compute='_compute_kecamatan_count'
    )

    _sql_constraints = [
        ('kode_uniq', 'UNIQUE(kode)', 'Kode Kota/Kabupaten harus unik!'),
    ]

    @api.depends('kecamatan_ids')
    def _compute_kecamatan_count(self):
        for rec in self:
            rec.kecamatan_count = len(rec.kecamatan_ids)

    def name_get(self):
        return [(r.id, f"[{r.kode}] {r.nama}") for r in self]


class KaKecamatan(models.Model):
    _name = 'ka.wilayah.kecamatan'
    _description = 'Kecamatan'
    _rec_name = 'nama'
    _order = 'kode'

    kode = fields.Char(string='Kode Kecamatan', required=True, size=10)
    nama = fields.Char(string='Nama Kecamatan', required=True)
    kota_id = fields.Many2one(
        'ka.wilayah.kota', string='Kota/Kabupaten', required=True, ondelete='restrict'
    )
    provinsi_id = fields.Many2one(
        'ka.wilayah.provinsi', related='kota_id.provinsi_id',
        store=True, readonly=True
    )
    active = fields.Boolean(default=True)

    desa_ids = fields.One2many(
        'ka.wilayah.desa', 'kecamatan_id', string='Daftar Desa'
    )
    desa_count = fields.Integer(
        string='Jumlah Desa', compute='_compute_desa_count'
    )

    _sql_constraints = [
        ('kode_uniq', 'UNIQUE(kode)', 'Kode Kecamatan harus unik!'),
    ]

    @api.depends('desa_ids')
    def _compute_desa_count(self):
        for rec in self:
            rec.desa_count = len(rec.desa_ids)

    def name_get(self):
        return [(r.id, f"[{r.kode}] {r.nama}") for r in self]


class KaDesa(models.Model):
    _name = 'ka.wilayah.desa'
    _description = 'Desa / Kelurahan'
    _rec_name = 'nama'
    _order = 'kode'

    kode = fields.Char(string='Kode Desa', required=True, size=10)
    nama = fields.Char(string='Nama Desa', required=True)
    kecamatan_id = fields.Many2one(
        'ka.wilayah.kecamatan', string='Kecamatan', required=True, ondelete='restrict'
    )
    kota_id = fields.Many2one(
        'ka.wilayah.kota', related='kecamatan_id.kota_id',
        store=True, readonly=True, string='Kota/Kabupaten'
    )
    provinsi_id = fields.Many2one(
        'ka.wilayah.provinsi', related='kecamatan_id.provinsi_id',
        store=True, readonly=True, string='Provinsi'
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('kode_uniq', 'UNIQUE(kode)', 'Kode Desa harus unik!'),
    ]

    def name_get(self):
        return [(r.id, f"[{r.kode}] {r.nama}") for r in self]
