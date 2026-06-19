# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaKasbankBalance(models.Model):
    """Saldo Kas/Bank Harian — header per tanggal (sheet KASBANK dinormalisasi
    dari wide ke long). Tiap baris = saldo satu akun pada tanggal tersebut.
    """
    _name = 'ka.kasbank.balance'
    _description = 'Saldo Kas/Bank Harian'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'date desc'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Mata Uang',
        default=lambda self: self.env.company.currency_id)
    date = fields.Date(string='Tanggal', required=True, index=True,
                       default=fields.Date.context_today, tracking=True)
    line_ids = fields.One2many('ka.kasbank.balance.line', 'balance_id', string='Rincian Saldo')
    total_balance = fields.Monetary(
        string='Total Saldo', currency_field='currency_id',
        compute='_compute_total_balance', store=True, tracking=True)
    note = fields.Text(string='Catatan')

    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('uniq_date_company', 'unique(date, company_id)',
         'Sudah ada catatan saldo untuk tanggal & unit ini.'),
    ]

    @api.depends('line_ids.balance')
    def _compute_total_balance(self):
        for rec in self:
            rec.total_balance = sum(rec.line_ids.mapped('balance'))

    @api.depends('date')
    def _compute_display_name(self):
        for rec in self:
            tgl = fields.Date.to_string(rec.date) if rec.date else ''
            rec.display_name = _('Saldo %s') % tgl if tgl else _('Saldo')

    # ── Auto-populate baris dari akun aktif ──
    def _populate_lines(self):
        """Tambahkan satu baris per akun aktif yang belum ada (saldo 0)."""
        Line = self.env['ka.kasbank.balance.line']
        Account = self.env['ka.kasbank.account']
        for rec in self:
            existing = rec.line_ids.mapped('account_id').ids
            domain = [('active', '=', True)]
            if rec.company_id:
                domain += ['|', ('company_id', '=', rec.company_id.id), ('company_id', '=', False)]
            accounts = Account.search(domain, order='sequence, name')
            new_lines = [
                {'balance_id': rec.id, 'account_id': acc.id, 'balance': 0.0}
                for acc in accounts if acc.id not in existing
            ]
            if new_lines:
                Line.create(new_lines)

    def action_populate_lines(self):
        """Tombol: muat akun Kas/Bank yang belum ada ke dalam rincian."""
        self._populate_lines()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Akun Dimuat'),
                'message': _('Akun Kas/Bank aktif yang belum ada telah ditambahkan.'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.line_ids:
                rec._populate_lines()
        return records


class KaKasbankBalanceLine(models.Model):
    """Baris saldo per akun dalam satu snapshot harian."""
    _name = 'ka.kasbank.balance.line'
    _description = 'Baris Saldo Kas/Bank'
    _order = 'balance_id, account_sequence, id'

    balance_id = fields.Many2one(
        'ka.kasbank.balance', string='Saldo Harian', required=True,
        ondelete='cascade', index=True)
    company_id = fields.Many2one(
        'res.company', related='balance_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(
        'res.currency', related='balance_id.currency_id', store=True, readonly=True)
    date = fields.Date(related='balance_id.date', store=True, readonly=True)
    account_id = fields.Many2one(
        'ka.kasbank.account', string='Akun', required=True)
    account_type = fields.Selection(
        related='account_id.account_type', store=True, readonly=True)
    account_sequence = fields.Integer(
        related='account_id.sequence', store=True, readonly=True)
    balance = fields.Monetary(string='Saldo', currency_field='currency_id')

    _sql_constraints = [
        ('uniq_account_per_snapshot', 'unique(balance_id, account_id)',
         'Akun ini sudah tercatat pada snapshot tanggal tersebut.'),
    ]
