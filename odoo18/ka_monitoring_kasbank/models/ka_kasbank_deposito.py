# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaKasbankDeposito(models.Model):
    """Deposito berjangka per bank (sheet KASBANK bagian Deposito / DATA bag. B)."""
    _name = 'ka.kasbank.deposito'
    _description = 'Deposito'
    _inherit = ['mail.thread']
    _rec_name = 'display_name'
    _order = 'maturity_date, id'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Mata Uang',
        default=lambda self: self.env.company.currency_id)
    name = fields.Char(string='No. Bilyet/Referensi')
    bank_id = fields.Many2one('res.bank', string='Bank', required=True, tracking=True)
    amount = fields.Monetary(string='Nominal', currency_field='currency_id', tracking=True)
    placement_date = fields.Date(string='Tgl Penempatan', tracking=True)
    maturity_date = fields.Date(string='Tgl Pencairan', tracking=True,
                                help='Tanggal jatuh tempo / pencairan deposito.')
    interest_rate = fields.Float(string='Bunga (%)', digits=(5, 2))
    state = fields.Selection(
        [('active', 'Aktif'), ('matured', 'Cair')],
        string='Status', default='active', required=True, tracking=True)
    note = fields.Text(string='Catatan')

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('bank_id', 'maturity_date', 'name')
    def _compute_display_name(self):
        for rec in self:
            if rec.name:
                rec.display_name = rec.name
            else:
                bank = rec.bank_id.name or _('Deposito')
                tgl = fields.Date.to_string(rec.maturity_date) if rec.maturity_date else ''
                rec.display_name = f"{bank} · {tgl}" if tgl else bank

    def action_set_matured(self):
        self.write({'state': 'matured'})

    def action_set_active(self):
        self.write({'state': 'active'})
