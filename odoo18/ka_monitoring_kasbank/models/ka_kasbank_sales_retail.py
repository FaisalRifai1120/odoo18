# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaKasbankSalesRetail(models.Model):
    """Penjualan Gula Ritel — per invoice (sheet Penjualan Ritel).
    Catatan: refund tampil sebagai qty/nilai negatif, jadi tidak diberi
    constraint non-negatif.
    """
    _name = 'ka.kasbank.sales.retail'
    _description = 'Penjualan Gula Ritel'
    _inherit = ['mail.thread']
    _order = 'invoice_date desc, id'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Mata Uang',
        default=lambda self: self.env.company.currency_id)

    partner_id = fields.Many2one('res.partner', string='Pelanggan', index=True)
    customer_code = fields.Char(string='Kode Pelanggan', index=True)
    segment = fields.Selection(
        [('ORG', 'ORG'), ('GOV', 'GOV'), ('ECO', 'ECO'), ('GTD', 'GTD'),
         ('MTI', 'MTI'), ('INT', 'INT'), ('HRK', 'HRK'), ('MTK', 'MTK'),
         ('DTB', 'DTB'), ('KOP', 'KOP')],
        string='Segmen', index=True)
    so_number = fields.Char(string='Nomor SO')
    delivery_order = fields.Char(string='Surat Jalan')
    driver = fields.Char(string='Driver')
    invoice_number = fields.Char(string='Nomor Invoice', index=True, tracking=True)
    invoice_date = fields.Date(string='Tanggal Invoice', index=True)
    due_date = fields.Date(string='Jatuh Tempo')
    qty_kg = fields.Float(string='Jumlah Barang (kg)', digits=(16, 2))
    price_unit = fields.Monetary(string='Harga Satuan', currency_field='currency_id')
    invoice_value = fields.Monetary(string='Nilai Invoice', currency_field='currency_id',
                                    compute='_compute_invoice_value', store=True)
    amount_paid = fields.Monetary(string='Jumlah Dibayar', currency_field='currency_id')
    payment_status = fields.Selection(
        [('open', 'Open'), ('paid', 'Paid'), ('overdue', 'Overdue')],
        string='Status Bayar', default='open', required=True, tracking=True)
    is_overdue = fields.Boolean(string='Lewat Jatuh Tempo',
                                compute='_compute_is_overdue', store=True)
    payment_date = fields.Date(string='Tgl Bayar AR')
    paid_month = fields.Char(string='Bulan Lunas')
    sale_month = fields.Char(string='Bulan Penjualan')
    note = fields.Text(string='Catatan')

    @api.depends('qty_kg', 'price_unit')
    def _compute_invoice_value(self):
        for rec in self:
            rec.invoice_value = (rec.qty_kg or 0.0) * (rec.price_unit or 0.0)

    @api.depends('payment_status', 'due_date')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(
                rec.payment_status != 'paid' and rec.due_date and rec.due_date < today
            )

    def action_mark_paid(self):
        self.write({'payment_status': 'paid'})
