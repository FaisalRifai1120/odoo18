# -*- coding: utf-8 -*-
from odoo import models, fields


class KaJenisTruk(models.Model):
    _name = 'ka.jenis.truk'
    _description = 'Master Jenis Truk'
    _rec_name = 'nama'
    _order = 'kode'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True,
        default=lambda self: self.env.company, index=True
    )
    kode = fields.Char(string='Kode', required=True, size=10)
    nama = fields.Char(string='Nama Jenis Truk', required=True)
    keterangan = fields.Char(string='Keterangan')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('kode_company_uniq', 'UNIQUE(kode, company_id)', 'Kode Jenis Truk harus unik per unit!'),
    ]

    def name_get(self):
        return [(r.id, f"[{r.kode}] {r.nama}") for r in self]
