# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaKasbankSalesBulk(models.Model):
    """Penjualan Gula Bulk — kontrak per No. SP (sheet Penjualan Bulk)."""
    _name = 'ka.kasbank.sales.bulk'
    _description = 'Penjualan Gula Bulk'
    _inherit = ['mail.thread']
    _order = 'date desc, id'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Mata Uang',
        default=lambda self: self.env.company.currency_id)

    sp_number = fields.Char(string='No. SP', index=True, tracking=True)
    date = fields.Date(string='Tanggal', index=True, default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string='Pembeli', index=True)
    production_year = fields.Integer(
        string='Tahun Produksi',
        default=lambda self: fields.Date.context_today(self).year)
    product_id = fields.Many2one('ka.kasbank.product', string='Jenis Gula')
    quantity = fields.Float(string='Kuantum (Ton)', digits=(16, 3))
    price_unit = fields.Monetary(string='Harga (Rp/Ton)', currency_field='currency_id')
    amount = fields.Monetary(string='Jumlah (Rp)', currency_field='currency_id',
                             compute='_compute_amount', store=True)
    payment_date = fields.Char(string='Tanggal Bayar',
                               help='Bisa berisi lebih dari satu tanggal (cicilan).')
    state = fields.Selection(
        [('open', 'Belum Lunas'), ('lunas', 'Lunas')],
        string='Status', default='open', required=True, tracking=True)
    note = fields.Text(string='Catatan')

    @api.depends('quantity', 'price_unit')
    def _compute_amount(self):
        for rec in self:
            rec.amount = (rec.quantity or 0.0) * (rec.price_unit or 0.0)

    def action_set_lunas(self):
        self.write({'state': 'lunas'})

    def action_set_open(self):
        self.write({'state': 'open'})
