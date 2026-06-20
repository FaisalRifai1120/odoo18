# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaKasbankDashboard(models.TransientModel):
    _name = 'ka.kasbank.dashboard'
    _description = 'Dashboard Monitoring Kas/Bank & Persediaan'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company',
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(
        'res.currency', compute='_compute_currency', readonly=True)
    refresh_trigger = fields.Datetime(default=fields.Datetime.now)
    as_of_date = fields.Date(string='Saldo per', compute='_compute_kpi')

    # Kas/Bank & likuiditas
    kas_bank_total = fields.Monetary(currency_field='currency_id', compute='_compute_kpi')
    deposito_aktif_total = fields.Monetary(currency_field='currency_id', compute='_compute_kpi')
    deposito_aktif_count = fields.Integer(compute='_compute_kpi')
    kas_plus_deposito = fields.Monetary(currency_field='currency_id', compute='_compute_kpi')

    # Kewajiban
    hutang_outstanding_total = fields.Monetary(currency_field='currency_id', compute='_compute_kpi')
    hutang_count = fields.Integer(compute='_compute_kpi')

    # Piutang
    piutang_bulk_open = fields.Monetary(currency_field='currency_id', compute='_compute_kpi')
    bulk_open_count = fields.Integer(compute='_compute_kpi')
    ritel_open = fields.Monetary(currency_field='currency_id', compute='_compute_kpi')
    ritel_overdue = fields.Monetary(currency_field='currency_id', compute='_compute_kpi')
    ritel_paid = fields.Monetary(currency_field='currency_id', compute='_compute_kpi')
    ritel_overdue_count = fields.Integer(compute='_compute_kpi')
    ritel_overdue_pct = fields.Float(string='% Overdue', compute='_compute_kpi')

    # Persediaan (Ton) — stok terkini = saldo akhir tanggal terbaru per produk
    persediaan_year_now = fields.Float(digits=(16, 3), compute='_compute_kpi')
    persediaan_year_prev = fields.Float(digits=(16, 3), compute='_compute_kpi')
    persediaan_year_now_label = fields.Char(compute='_compute_kpi')
    persediaan_year_prev_label = fields.Char(compute='_compute_kpi')

    @api.depends('company_id')
    def _compute_currency(self):
        for d in self:
            d.currency_id = (d.company_id or self.env.company).currency_id

    def _sum_group(self, model, domain, field):
        """Jumlah satu field via read_group (aman jika kosong). Return (sum, count)."""
        g = self.env[model].read_group(domain, [f'{field}:sum'], [])
        if g:
            return (g[0].get(field) or 0.0), (g[0].get('__count') or 0)
        return 0.0, 0

    def _sum_latest_stock(self, cid, year):
        """Total saldo_akhir tanggal TERBARU per produk untuk tahun produksi tsb."""
        Inv = self.env['ka.kasbank.inventory']
        groups = Inv.read_group(
            [('company_id', '=', cid), ('production_year', '=', year)],
            ['product_id'], ['product_id'])
        total = 0.0
        for grp in groups:
            pid = grp['product_id'][0] if grp.get('product_id') else False
            if not pid:
                continue
            rec = Inv.search(
                [('company_id', '=', cid), ('production_year', '=', year),
                 ('product_id', '=', pid)],
                order='date desc', limit=1)
            total += rec.saldo_akhir
        return total

    @api.depends('company_id', 'refresh_trigger')
    def _compute_kpi(self):
        today = fields.Date.context_today(self)
        for dash in self:
            cid = (dash.company_id or self.env.company).id

            bal = self.env['ka.kasbank.balance'].search(
                [('company_id', '=', cid)], order='date desc', limit=1)
            dash.kas_bank_total = bal.total_balance if bal else 0.0
            dash.as_of_date = bal.date if bal else False

            dep_sum, dep_cnt = self._sum_group(
                'ka.kasbank.deposito',
                [('company_id', '=', cid), ('state', '=', 'active')], 'amount')
            dash.deposito_aktif_total = dep_sum
            dash.deposito_aktif_count = dep_cnt
            dash.kas_plus_deposito = dash.kas_bank_total + dep_sum

            loan_sum, loan_cnt = self._sum_group(
                'ka.kasbank.loan',
                [('company_id', '=', cid), ('state', '=', 'outstanding')], 'amount')
            dash.hutang_outstanding_total = loan_sum
            dash.hutang_count = loan_cnt

            bulk_sum, bulk_cnt = self._sum_group(
                'ka.kasbank.sales.bulk',
                [('company_id', '=', cid), ('state', '=', 'open')], 'amount')
            dash.piutang_bulk_open = bulk_sum
            dash.bulk_open_count = bulk_cnt

            open_sum, _c = self._sum_group(
                'ka.kasbank.sales.retail',
                [('company_id', '=', cid), ('payment_status', '=', 'open')], 'invoice_value')
            over_sum, over_cnt = self._sum_group(
                'ka.kasbank.sales.retail',
                [('company_id', '=', cid), ('payment_status', '=', 'overdue')], 'invoice_value')
            paid_sum, _p = self._sum_group(
                'ka.kasbank.sales.retail',
                [('company_id', '=', cid), ('payment_status', '=', 'paid')], 'invoice_value')
            dash.ritel_open = open_sum
            dash.ritel_overdue = over_sum
            dash.ritel_paid = paid_sum
            dash.ritel_overdue_count = over_cnt
            piutang = open_sum + over_sum
            dash.ritel_overdue_pct = (100.0 * over_sum / piutang) if piutang else 0.0

            yr_now = today.year
            yr_prev = yr_now - 1
            dash.persediaan_year_now_label = str(yr_now)
            dash.persediaan_year_prev_label = str(yr_prev)
            dash.persediaan_year_now = self._sum_latest_stock(cid, yr_now)
            dash.persediaan_year_prev = self._sum_latest_stock(cid, yr_prev)

    # ───────────────────────── aksi ─────────────────────────
    def action_refresh(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dashboard Kas/Bank'),
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'current',
            'context': dict(self.env.context, default_company_id=(self.company_id or self.env.company).id),
        }

    def _drill(self, name, model, domain):
        cid = (self.company_id or self.env.company).id
        return {
            'type': 'ir.actions.act_window', 'name': name, 'res_model': model,
            'view_mode': 'list,form', 'target': 'current',
            'domain': [('company_id', '=', cid)] + domain,
        }

    def action_open_deposito_aktif(self):
        return self._drill(_('Deposito Aktif'), 'ka.kasbank.deposito', [('state', '=', 'active')])

    def action_open_hutang(self):
        return self._drill(_('Hutang Outstanding'), 'ka.kasbank.loan', [('state', '=', 'outstanding')])

    def action_open_bulk_open(self):
        return self._drill(_('Piutang Bulk (Open)'), 'ka.kasbank.sales.bulk', [('state', '=', 'open')])

    def action_open_ritel_overdue(self):
        return self._drill(_('Piutang Ritel Overdue'), 'ka.kasbank.sales.retail',
                           [('payment_status', '=', 'overdue')])

    def action_open_ritel_open(self):
        return self._drill(_('Piutang Ritel Open'), 'ka.kasbank.sales.retail',
                           [('payment_status', '=', 'open')])
