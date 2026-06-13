# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import AccessError


class KaSitaRegister(models.Model):
    _name = 'ka.sita.register'
    _description = 'Register SITA'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'kode_register'
    _order = 'kode_register'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True,
        default=lambda self: self.env.company, index=True
    )
    kode_register = fields.Char(string='Kode Register', required=True, tracking=True)
    nama_register = fields.Char(string='Nama Register', required=True, tracking=True)
    jenis_register = fields.Selection([
        ('TR', 'TR (Tebu Rakyat)'),
        ('TS', 'TS (Tebu Sendiri)'),
    ], string='Jenis Register', required=True, tracking=True)
    metode = fields.Selection([
        ('SBH', 'SBH (Sistem Bagi Hasil)'),
        ('SPT', 'SPT (Sistem Pembelian Tebu Tunai)'),
    ], string='Metode', required=True, tracking=True)
    jenis_pembayaran = fields.Selection([
        ('Harian',  'Harian'),
        ('Periode', 'Periode'),
    ], string='Jenis Pembayaran', required=True, tracking=True)

    kud_id = fields.Many2one('ka.kud', string='KUD', required=False, ondelete='restrict', tracking=True)
    desa_id = fields.Many2one('ka.wilayah.desa', string='Desa', ondelete='restrict', tracking=True)
    kecamatan_id = fields.Many2one('ka.wilayah.kecamatan', string='Kecamatan', ondelete='restrict', tracking=True)

    petani_id = fields.Many2one('ka.petani', string='Petani', ondelete='restrict', tracking=True)
    account_petani_id = fields.Many2one('ka.petani', string='Account Petani', ondelete='restrict', tracking=True)

    ppl_id = fields.Many2one(
        'ka.user.profile',
        string='PPL',
        domain="[('role', '=', 'ppl')]",
        tracking=True,
        ondelete='set null'
    )

    is_transfer = fields.Boolean(string='Transfer', default=False, tracking=True)
    no_rekening = fields.Char(string='No. Rekening', tracking=True)
    nama_bank = fields.Char(string='Nama Bank', tracking=True)
    nama_rekening = fields.Char(string='Nama Rekening', tracking=True)
    no_ktp = fields.Char(string='Nomor KTP', size=16, tracking=True)

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('kode_register_company_uniq', 'UNIQUE(kode_register, company_id)', 'Kode Register harus unik per unit!'),
    ]

    @api.onchange('petani_id')
    def _onchange_petani_id(self):
        if self.petani_id:
            p = self.petani_id
            self.no_rekening   = p.no_rekening   or self.no_rekening
            self.nama_bank     = p.nama_bank     or self.nama_bank
            self.nama_rekening = p.nama_rekening or self.nama_rekening
            self.no_ktp        = p.no_ktp        or self.no_ktp
            self.account_petani_id = p.id
            if p.ppl_id:
                self.ppl_id = p.ppl_id

    @api.onchange('account_petani_id')
    def _onchange_account_petani_id(self):
        if self.account_petani_id:
            p = self.account_petani_id
            self.no_rekening   = p.no_rekening   or self.no_rekening
            self.nama_bank     = p.nama_bank     or self.nama_bank
            self.nama_rekening = p.nama_rekening or self.nama_rekening
            if not self.petani_id:
                self.petani_id = p.id
            if p.ppl_id and not self.ppl_id:
                self.ppl_id = p.ppl_id

    @api.onchange('desa_id')
    def _onchange_desa_id(self):
        if self.desa_id:
            self.kecamatan_id = self.desa_id.kecamatan_id

    def name_get(self):
        return [(r.id, r.kode_register or f'Register #{r.id}') for r in self]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_petani_jumlah_register()
        return records

    def write(self, vals):
        old_petani = self.mapped('petani_id')
        res = super().write(vals)
        if 'petani_id' in vals:
            new_petani = self.mapped('petani_id')
            (old_petani | new_petani)._recompute_jumlah_register()
        return res

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
    _inherit = 'ka.petani'

    register_ids = fields.One2many('ka.sita.register', 'petani_id', string='Daftar Register')

    def _recompute_jumlah_register(self):
        for rec in self:
            rec.jumlah_register = self.env['ka.sita.register'].search_count(
                [('petani_id', '=', rec.id)]
            )


class KaMailMessageInherit(models.Model):
    """Batasi hapus pesan chatter — hanya Administrator KA yang boleh."""
    _inherit = 'mail.message'

    def unlink(self):
        ka_models = {'ka.sita.register', 'ka.petani', 'ka.kud', 'ka.user.profile'}
        is_admin = (
            self.env.user._is_admin() or
            self.env.user.has_group('ka_user_management.group_ka_admin')
        )
        if not is_admin:
            ka_messages = self.filtered(lambda m: m.model in ka_models)
            if ka_messages:
                raise AccessError('Hanya Administrator yang dapat menghapus log aktivitas.')
        return super().unlink()
