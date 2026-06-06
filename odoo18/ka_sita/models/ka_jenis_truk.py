# -*- coding: utf-8 -*-
from odoo import models, fields


class KaJenisTruk(models.Model):
    _name = 'ka.jenis.truk'
    _description = 'Master Jenis Truk'
    _rec_name = 'nama'
    _order = 'kode'

    kode = fields.Char(string='Kode', required=True, size=10)
    nama = fields.Char(string='Nama Jenis Truk', required=True)
    keterangan = fields.Char(string='Keterangan')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('kode_uniq', 'UNIQUE(kode)', 'Kode Jenis Truk harus unik!'),
    ]

    def name_get(self):
        return [(r.id, f"[{r.kode}] {r.nama}") for r in self]
