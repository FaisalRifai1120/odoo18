# -*- coding: utf-8 -*-
from odoo import models, fields


class KaKud(models.Model):
    _name = 'ka.kud'
    _description = 'KUD (Koperasi Unit Desa)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'nama'
    _order = 'kode'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True,
        default=lambda self: self.env.company, index=True
    )
    kode = fields.Char(string='Kode KUD', required=True, size=20, tracking=True)
    nama = fields.Char(string='Nama KUD', required=True, tracking=True)
    kota_id = fields.Many2one('ka.wilayah.kota', string='Kota/Kabupaten', required=True, tracking=True, ondelete='restrict')
    provinsi_id = fields.Many2one('ka.wilayah.provinsi', related='kota_id.provinsi_id', store=True, readonly=True, string='Provinsi')
    kota_nama = fields.Char(string='Nama Kota (bebas)', tracking=True)
    alamat = fields.Text(string='Alamat Lengkap', tracking=True)
    no_telepon = fields.Char(string='No. Telepon', tracking=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [('kode_company_uniq', 'UNIQUE(kode, company_id)', 'Kode KUD harus unik per unit!')]

    def name_get(self):
        return [(r.id, f"[{r.kode}] {r.nama}") for r in self]
