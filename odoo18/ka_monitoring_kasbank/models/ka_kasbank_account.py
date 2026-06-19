# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaKasbankAccount(models.Model):
    """Master Akun Kas/Bank — sumber kolom pada snapshot saldo harian
    (Kas, Mandiri Bisnis, BNI, UOB, Mandiri Retail, Kas Surabaya, dst).
    """
    _name = 'ka.kasbank.account'
    _description = 'Master Akun Kas/Bank'
    _order = 'sequence, name'

    name = fields.Char(string='Nama Akun', required=True)
    code = fields.Char(string='Kode')
    account_type = fields.Selection(
        [('cash', 'Kas'), ('bank', 'Bank')],
        string='Tipe', required=True, default='bank')
    account_number = fields.Char(string='No. Rekening')
    bank_id = fields.Many2one('res.bank', string='Bank')
    currency_id = fields.Many2one(
        'res.currency', string='Mata Uang',
        default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', string='Unit/Company',
        default=lambda self: self.env.company, index=True)
    sequence = fields.Integer(string='Urutan', default=10)
    active = fields.Boolean(string='Aktif', default=True)
    note = fields.Char(string='Keterangan')

    # journal_id (account.journal) sengaja BELUM ditambahkan —
    # akan menyusul saat integrasi modul akuntansi (ka_account) tersedia.
