# -*- coding: utf-8 -*-
from odoo import models, fields, api


class KaMbs(models.Model):
    _name = 'ka.mbs'
    _description = 'Master MBS (Masakan Brix Standar)'
    _rec_name = 'label'
    _order = 'kode'

    kode = fields.Integer(
        string='Kode MBS', required=True,
        help='Kode angka MBS dari sistem timbangan'
    )
    label = fields.Char(
        string='Label MBS', required=True,
        help='Keterangan MBS yang tampil di Odoo'
    )
    keterangan = fields.Text(string='Keterangan Tambahan')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('kode_uniq', 'UNIQUE(kode)', 'Kode MBS harus unik!'),
    ]

    def name_get(self):
        return [(r.id, f"[{r.kode}] {r.label}") for r in self]
