# -*- coding: utf-8 -*-
from odoo import models, fields, api


class KaSptaNomor(models.Model):
    """Nomor SPTA individual yang di-generate dari ka.spta."""
    _name = 'ka.spta.nomor'
    _description = 'Nomor SPTA Individual'
    _rec_name = 'no_spta'
    _order = 'no_spta'

    spta_id = fields.Many2one(
        'ka.spta', string='SPTA Induk',
        required=True, ondelete='cascade'
    )
    no_spta = fields.Char(string='No. SPTA', required=True, index=True)
    tanggal = fields.Date(
        related='spta_id.tanggal', store=True, readonly=True
    )
    register_id = fields.Many2one(
        related='spta_id.register_id', store=True, readonly=True
    )
    petani_id = fields.Many2one(
        related='spta_id.petani_id', store=True, readonly=True
    )
    kud_id = fields.Many2one(
        related='spta_id.kud_id', store=True, readonly=True
    )
    jenis_tebang = fields.Selection(
        related='spta_id.jenis_tebang', store=True, readonly=True
    )
    jenis_truk_id = fields.Many2one(
        related='spta_id.jenis_truk_id', store=True, readonly=True
    )
    tgl_mulai = fields.Datetime(
        related='spta_id.tgl_mulai', store=True, readonly=True
    )
    tgl_selesai = fields.Datetime(
        related='spta_id.tgl_selesai', store=True, readonly=True
    )
    state = fields.Selection([
        ('available',  'Tersedia'),
        ('used',       'Terpakai'),
        ('cancel',     'Dibatalkan'),
    ], string='Status', default='available')
    is_distributed = fields.Boolean(
        string='Sudah Cetak', default=False
    )

    _sql_constraints = [
        ('no_spta_uniq', 'UNIQUE(no_spta)', 'No. SPTA harus unik!'),
    ]

    def name_get(self):
        return [(r.id, r.no_spta) for r in self]
