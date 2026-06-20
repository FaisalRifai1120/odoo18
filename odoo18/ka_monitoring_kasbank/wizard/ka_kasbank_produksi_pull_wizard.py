# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class KaKasbankProduksiPullWizard(models.TransientModel):
    _name = 'ka.kasbank.produksi.pull.wizard'
    _description = 'Tarik Produksi Giling ke Persediaan'

    date_from = fields.Date(string='Dari Tanggal', required=True,
                            default=lambda s: fields.Date.context_today(s).replace(day=1))
    date_to = fields.Date(string='Sampai Tanggal', required=True,
                          default=fields.Date.context_today)
    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True,
        default=lambda self: self.env.company,
        help='Unit pabrik tempat giling (mis. PG Kebon Agung).')
    production_year = fields.Integer(
        string='Tahun Produksi (Eks)', required=True,
        default=lambda s: fields.Date.context_today(s).year,
        help='Booking produksi ke persediaan tahun produksi ini (mis. 2026).')
    create_missing = fields.Boolean(
        string='Buat baris persediaan bila belum ada', default=False,
        help='Jika dicentang, baris persediaan harian dibuat bila belum ada '
             '(saldo awal & penjualan = 0). Jika tidak, hanya memperbarui baris yang sudah ada.')

    state = fields.Selection([('draft', 'Draft'), ('done', 'Selesai')], default='draft')
    result_summary = fields.Text(string='Ringkasan', readonly=True)

    def action_pull(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("'Dari Tanggal' tidak boleh melebihi 'Sampai Tanggal'."))

        # mapping produk: giling_key → produk kasbank
        products = self.env['ka.kasbank.product'].search([('giling_key', '!=', False)])
        if not products:
            raise UserError(_(
                "Belum ada Produk yang dipetakan ke produksi giling.\n"
                "Set field 'Sumber Produksi Giling' di Konfigurasi → Produk Gula dulu "
                "(mis. GKP 50 KG → GKP)."))
        prod_by_key = {p.giling_key: p for p in products}

        # baca Rincian Produksi giling (read-only, via sudo agar user kasbank tak perlu grup ka_monitoring)
        Produksi = self.env['ka.giling.produksi'].sudo()
        lines = Produksi.search([
            ('date', '>=', self.date_from), ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('product_key', 'in', list(prod_by_key.keys())),
        ])

        # agregasi qty per (tanggal, key) — bisa ada >1 giling/hari
        agg = defaultdict(float)
        for ln in lines:
            agg[(ln.date, ln.product_key)] += ln.qty or 0.0

        Inv = self.env['ka.kasbank.inventory']
        created = updated = skipped = 0
        for (d, key), qty in agg.items():
            product = prod_by_key[key]
            existing = Inv.search([
                ('date', '=', d), ('company_id', '=', self.company_id.id),
                ('product_id', '=', product.id), ('production_year', '=', self.production_year),
            ], limit=1)
            if existing:
                existing.produksi = qty
                updated += 1
            elif self.create_missing:
                Inv.create({
                    'date': d, 'company_id': self.company_id.id,
                    'product_id': product.id, 'production_year': self.production_year,
                    'produksi': qty,
                })
                created += 1
            else:
                skipped += 1

        summary = _(
            "Tarik produksi %(from)s s/d %(to)s (Eks %(yr)s):\n"
            "  • Produk dipetakan : %(pmap)s\n"
            "  • Baris diperbarui : %(u)s\n"
            "  • Baris dibuat     : %(c)s\n"
            "  • Dilewati (blm ada): %(s)s",
            **{'from': self.date_from, 'to': self.date_to, 'yr': self.production_year,
               'pmap': ", ".join(products.mapped('name')), 'u': updated, 'c': created, 's': skipped})
        self.write({'state': 'done', 'result_summary': summary})
        return {
            'type': 'ir.actions.act_window', 'res_model': self._name,
            'res_id': self.id, 'view_mode': 'form', 'target': 'new',
        }
