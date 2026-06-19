# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaKasbankLoan(models.Model):
    """Hutang/pinjaman bank (sheet DATA bag. D)."""
    _name = 'ka.kasbank.loan'
    _description = 'Hutang Bank'
    _inherit = ['mail.thread']
    _rec_name = 'display_name'
    _order = 'due_date, id'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Mata Uang',
        default=lambda self: self.env.company.currency_id)
    name = fields.Char(string='No. Pinjaman/Referensi')
    bank_id = fields.Many2one('res.bank', string='Bank', required=True, tracking=True)
    amount = fields.Monetary(string='Nilai Hutang', currency_field='currency_id', tracking=True)
    due_date = fields.Date(string='Tgl Jatuh Tempo', tracking=True)
    state = fields.Selection(
        [('outstanding', 'Outstanding'), ('paid', 'Lunas')],
        string='Status', default='outstanding', required=True, tracking=True)
    note = fields.Text(string='Catatan')

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('bank_id', 'due_date', 'name')
    def _compute_display_name(self):
        for rec in self:
            if rec.name:
                rec.display_name = rec.name
            else:
                bank = rec.bank_id.name or _('Hutang')
                tgl = fields.Date.to_string(rec.due_date) if rec.due_date else ''
                rec.display_name = f"{bank} · {tgl}" if tgl else bank

    def action_set_paid(self):
        self.write({'state': 'paid'})

    def action_set_outstanding(self):
        self.write({'state': 'outstanding'})
