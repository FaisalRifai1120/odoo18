# -*- coding: utf-8 -*-
import pytz
from datetime import datetime, time as dtime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

# Definisi "hari giling" untuk agregasi data Timbangan:
# dimulai pukul 06:00:00 dan berakhir 05:59:59 keesokan harinya, WAKTU PABRIK.
# Memakai zona tetap (bukan zona user) agar hasil konsisten untuk cron & semua user.
FACTORY_TZ = 'Asia/Jakarta'          # WIB (UTC+7) — zona operasional pabrik
GILING_DAY_START = dtime(6, 0, 0)    # jam mulai hari giling (06:00 waktu pabrik)


class KaGilingHarian(models.Model):
    """Laporan Harian Giling (DT_UMUM).

    Tebu tergiling (TR-SBH / TS / SPT) DIAGREGASI OTOMATIS dari ka.timbang.tebu
    berdasarkan klasifikasi register:
        - TR-SBH : register.jenis_register = 'TR' DAN metode = 'SBH'
        - TS     : register.jenis_register = 'TS'
        - SPT    : register.metode = 'SPT'

    Seluruh perhitungan monitoring SBH & SPT (laba/rugi) dihitung di sini sebagai
    stored computed fields, lalu diproyeksikan oleh SQL view monitoring.sbh/spt/rekap.
    """
    _name = 'ka.giling.harian'
    _description = 'Laporan Harian Giling'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'date DESC'

    # ── Identitas ──────────────────────────────────────────────
    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company
    )
    date = fields.Date(string='Tanggal', required=True, index=True,
                       default=fields.Date.context_today, tracking=True)
    gil_ke = fields.Integer(string='Giling ke-', tracking=True,
                            help='Nomor urut hari giling dalam musim')
    season_id = fields.Many2one(
        'ka.giling.season', string='Musim',
        compute='_compute_season', store=True, index=True
    )
    periode_id = fields.Many2one(
        'ka.giling.periode', string='Periode',
        compute='_compute_periode', store=True, index=True
    )
    periode_code = fields.Char(string='Kode Periode',
                               related='periode_id.code', store=True, readonly=True)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    # Trigger untuk memaksa recompute finansial (mis. saat harga/parameter berubah)
    recompute_trigger = fields.Datetime(string='Trigger Hitung', default=fields.Datetime.now)

    # ── Tebu Tergiling (OTOMATIS dari ka_timbangan, dapat dikoreksi manual) ──
    tebu_tr_sbh = fields.Float(string='Tebu TR-SBH (Ton)', digits=(16, 2), tracking=True,
                               help='Otomatis dari timbangan: register TR + metode SBH')
    tebu_ts = fields.Float(string='Tebu TS (Ton)', digits=(16, 2), tracking=True,
                           help='Otomatis dari timbangan: register TS')
    tebu_spt = fields.Float(string='Tebu SPT (Ton)', digits=(16, 2), tracking=True,
                            help='Otomatis dari timbangan: register metode SPT')
    tebu_total = fields.Float(string='Total Tebu (Ton)', digits=(16, 2),
                              compute='_compute_tebu_total', store=True)

    # ── Rendemen Sementara (input lab) ─────────────────────────
    rend_tr = fields.Float(string='Rend. Sementara TR (%)', digits=(8, 4), tracking=True)
    rend_ts = fields.Float(string='Rend. Sementara TS (%)', digits=(8, 4), tracking=True)
    rend_spt = fields.Float(string='Rend. Sementara SPT (%)', digits=(8, 4), tracking=True)
    rend_rata = fields.Float(string='Rend. Rata-rata (%)', digits=(8, 4),
                             compute='_compute_rend_rata', store=True)

    # ── Kapasitas ──────────────────────────────────────────────
    kapasitas_brutto = fields.Float(string='Kapasitas Giling Brutto (TCD)', digits=(16, 2),
                                    compute='_compute_kapasitas', store=True)

    # ── Produksi (input) ───────────────────────────────────────
    rs_in = fields.Float(string='RS Diolah In (Ton)', digits=(16, 3), tracking=True)
    prod_gkp = fields.Float(string='Produksi GKP (Ton)', digits=(16, 3), tracking=True)
    gula_ex2025 = fields.Float(string='Gula @50kg ex-2025 (Ton)', digits=(16, 3), tracking=True)
    gkp_premium = fields.Float(string='GKP-Premium (Ton)', digits=(16, 3), tracking=True)
    gula_reject = fields.Float(string='Gula Reject (Ton)', digits=(16, 3), tracking=True)
    produk_rs = fields.Float(string='Produk RS (Ton)', digits=(16, 3), tracking=True)
    tetes_ton = fields.Float(string='Tetes (Ton)', digits=(16, 3), tracking=True)
    total_produksi = fields.Float(string='Total Produksi Gula (Ton)', digits=(16, 3),
                                  compute='_compute_total_produksi', store=True)
    pct_tetes = fields.Float(string='Tetes % Tebu', digits=(8, 4),
                             compute='_compute_pct_tetes', store=True)

    # ── Ampas / Bahan Bakar / Listrik / Uap (input) ────────────
    ampas = fields.Float(string='Produksi Ampas (Ton)', digits=(16, 2), tracking=True)
    bb_sekam = fields.Float(string='Bahan Bakar Sekam (Ton)', digits=(16, 2), tracking=True)
    listrik_pg = fields.Float(string='Listrik PG (KWH)', digits=(16, 2), tracking=True)
    listrik_pln = fields.Float(string='Listrik PLN (KWH)', digits=(16, 2), tracking=True)
    prod_uap = fields.Float(string='Produksi Uap (Ton/hari)', digits=(16, 2), tracking=True)

    # ── Jam Berhenti (input + hitung) ──────────────────────────
    jam_riil_pabrik = fields.Float(string='Jam Berhenti Riil Pabrik (Jam)', digits=(8, 2), tracking=True)
    jam_riil_luar = fields.Float(string='Jam Berhenti Riil Luar (Jam)', digits=(8, 2), tracking=True)
    jam_total = fields.Float(string='Total Jam Berhenti (Jam)', digits=(8, 2),
                             compute='_compute_jam_total', store=True)
    jam_uraian = fields.Text(string='Keterangan Jam Berhenti')

    # ── Sisa Tebu Emplasemen (input) ───────────────────────────
    sisa_tebu_truck = fields.Integer(string='Sisa Tebu Emplasemen (Truck)')
    sisa_tebu_ton = fields.Float(string='Sisa Tebu (Ton)', digits=(16, 2))

    # ── Pengeluaran (input) ────────────────────────────────────
    keluar_shs = fields.Float(string='Pengeluaran SHS (Ton)', digits=(16, 3))
    keluar_tetes = fields.Float(string='Pengeluaran Tetes (Ton)', digits=(16, 3))
    keluar_ampas = fields.Float(string='Pengeluaran Ampas (Ton)', digits=(16, 3))

    notes = fields.Text(string='Catatan')

    # ── Analisa Lab (1 record/hari) ────────────────────────────
    analisa_ids = fields.One2many('ka.giling.analisa', 'giling_id', string='Analisa Lab')

    # ── Rincian Truk (digenerate dari ka_timbangan) ────────────
    truk_ids = fields.One2many('ka.giling.truk', 'giling_id', string='Rincian Truk')

    # ── Snapshot Konfigurasi (computed dari periode/harga/parameter) ──
    bagi_hasil_rate = fields.Float(string='Bagi Hasil (Kg/Ku)', digits=(12, 4),
                                   compute='_compute_financials', store=True)
    harga_gula = fields.Float(string='Harga Gula (Rp/kg)', digits=(16, 2),
                              compute='_compute_financials', store=True)
    harga_tetes = fields.Float(string='Harga Tetes (Rp/kg)', digits=(16, 2),
                               compute='_compute_financials', store=True)
    pembelian_spt = fields.Float(string='Pembelian SPT (Rp/Ku)', digits=(16, 2),
                                 compute='_compute_financials', store=True)
    biaya_produksi = fields.Float(string='Biaya Produksi (Rp/Ku)', digits=(16, 2),
                                  compute='_compute_financials', store=True)
    biaya_laba = fields.Float(string='Biaya + Laba (Rp/Ku)', digits=(16, 2),
                              compute='_compute_financials', store=True)
    faktor_gula = fields.Float(string='Faktor Gula', digits=(12, 4),
                               compute='_compute_financials', store=True)

    # ── Monitoring SBH (computed) ──────────────────────────────
    rend_sbh = fields.Float(string='Rend. SBH (%)', digits=(8, 4),
                            compute='_compute_financials', store=True)
    sbh_prod_gula = fields.Float(string='SBH Produksi Gula (Ton)', digits=(16, 3),
                                 compute='_compute_financials', store=True)
    sbh_prod_tetes = fields.Float(string='SBH Produksi Tetes (Ton)', digits=(16, 3),
                                  compute='_compute_financials', store=True)
    sbh_gula_milik_pg = fields.Float(string='SBH Gula Milik PG (Ton)', digits=(16, 3),
                                     compute='_compute_financials', store=True)
    sbh_tetes_milik_pg = fields.Float(string='SBH Tetes Milik PG (Ton)', digits=(16, 3),
                                      compute='_compute_financials', store=True)
    sbh_bagi_hasil_rp = fields.Float(string='SBH Bagi Hasil Gula (Rp/Ku)', digits=(16, 2),
                                     compute='_compute_financials', store=True)
    sbh_pendapatan = fields.Float(string='SBH Pendapatan (Rp/Ku)', digits=(16, 2),
                                  compute='_compute_financials', store=True)
    sbh_laba_biaya_ku = fields.Float(string='SBH Laba thd Biaya Produksi (Rp/Ku)', digits=(16, 2),
                                     compute='_compute_financials', store=True)
    sbh_laba_biaya_rp = fields.Float(string='SBH Laba thd Biaya Produksi (Rp)', digits=(18, 2),
                                     compute='_compute_financials', store=True)
    sbh_labarugi_ku = fields.Float(string='SBH Laba/Rugi Total (Rp/Ku)', digits=(16, 2),
                                   compute='_compute_financials', store=True)
    sbh_labarugi_rp = fields.Float(string='SBH Laba/Rugi Total (Rp)', digits=(18, 2),
                                   compute='_compute_financials', store=True)
    sbh_status = fields.Selection([('laba', 'Laba'), ('rugi', 'Rugi')],
                                  string='SBH Status', compute='_compute_financials', store=True)

    # ── Monitoring SPT (computed) ──────────────────────────────
    spt_prod_gula = fields.Float(string='SPT Produksi Gula (Ton)', digits=(16, 3),
                                 compute='_compute_financials', store=True)
    spt_prod_tetes = fields.Float(string='SPT Produksi Tetes (Ton)', digits=(16, 3),
                                  compute='_compute_financials', store=True)
    spt_pendapatan = fields.Float(string='SPT Pendapatan (Rp/Ku)', digits=(16, 2),
                                  compute='_compute_financials', store=True)
    spt_laba_pembelian = fields.Float(string='SPT Laba Pembelian (Rp/Ku)', digits=(16, 2),
                                      compute='_compute_financials', store=True)
    spt_laba_biaya_ku = fields.Float(string='SPT Laba thd Biaya Produksi (Rp/Ku)', digits=(16, 2),
                                     compute='_compute_financials', store=True)
    spt_laba_biaya_rp = fields.Float(string='SPT Laba thd Biaya Produksi (Rp)', digits=(18, 2),
                                     compute='_compute_financials', store=True)
    spt_labarugi_ku = fields.Float(string='SPT Laba/Rugi Total (Rp/Ku)', digits=(16, 2),
                                   compute='_compute_financials', store=True)
    spt_labarugi_rp = fields.Float(string='SPT Laba/Rugi Total (Rp)', digits=(18, 2),
                                   compute='_compute_financials', store=True)
    spt_status = fields.Selection([('laba', 'Laba'), ('rugi', 'Rugi')],
                                  string='SPT Status', compute='_compute_financials', store=True)

    # ── Total Gabungan ─────────────────────────────────────────
    labarugi_total_rp = fields.Float(string='Laba/Rugi Total SBH+SPT (Rp)', digits=(18, 2),
                                     compute='_compute_financials', store=True)

    _sql_constraints = [
        ('date_company_uniq', 'UNIQUE(date, company_id)',
         'Sudah ada Laporan Harian Giling untuk tanggal & unit ini!'),
    ]

    # ════════════════════════════════════════════════════════════
    #  COMPUTE — identitas & dasar
    # ════════════════════════════════════════════════════════════
    @api.depends('date', 'gil_ke', 'periode_code')
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.gil_ke:
                parts.append(_('Giling ke-%s') % rec.gil_ke)
            if rec.date:
                parts.append(rec.date.strftime('%d/%m/%Y'))
            rec.display_name = ' · '.join(parts) if parts else _('Hari Giling Baru')

    @api.depends('date')
    def _compute_season(self):
        Season = self.env['ka.giling.season']
        for rec in self:
            rec.season_id = Season.search([
                ('date_start', '<=', rec.date),
                ('date_end', '>=', rec.date),
            ], limit=1) if rec.date else False

    @api.depends('date')
    def _compute_periode(self):
        Periode = self.env['ka.giling.periode']
        for rec in self:
            rec.periode_id = Periode.search([
                ('date_start', '<=', rec.date),
            ], order='date_start desc', limit=1) if rec.date else False

    @api.depends('tebu_tr_sbh', 'tebu_ts', 'tebu_spt')
    def _compute_tebu_total(self):
        for rec in self:
            rec.tebu_total = (rec.tebu_tr_sbh or 0.0) + (rec.tebu_ts or 0.0) + (rec.tebu_spt or 0.0)

    @api.depends('tebu_tr_sbh', 'tebu_ts', 'tebu_spt', 'rend_tr', 'rend_ts', 'rend_spt', 'tebu_total')
    def _compute_rend_rata(self):
        for rec in self:
            if rec.tebu_total:
                rec.rend_rata = (
                    (rec.tebu_tr_sbh or 0.0) * (rec.rend_tr or 0.0)
                    + (rec.tebu_ts or 0.0) * (rec.rend_ts or 0.0)
                    + (rec.tebu_spt or 0.0) * (rec.rend_spt or 0.0)
                ) / rec.tebu_total
            else:
                rec.rend_rata = 0.0

    @api.depends('tebu_total', 'jam_total')
    def _compute_kapasitas(self):
        for rec in self:
            denom = 24.0 - (rec.jam_total or 0.0)
            rec.kapasitas_brutto = (rec.tebu_total * 24.0 / denom) if (rec.tebu_total and denom > 0) else 0.0

    @api.depends('prod_gkp', 'gkp_premium', 'gula_reject')
    def _compute_total_produksi(self):
        for rec in self:
            rec.total_produksi = (rec.prod_gkp or 0.0) + (rec.gkp_premium or 0.0) + (rec.gula_reject or 0.0)

    @api.depends('tetes_ton', 'tebu_total')
    def _compute_pct_tetes(self):
        for rec in self:
            rec.pct_tetes = (100.0 * rec.tetes_ton / rec.tebu_total) if rec.tebu_total else 0.0

    @api.depends('jam_riil_pabrik', 'jam_riil_luar')
    def _compute_jam_total(self):
        for rec in self:
            rec.jam_total = (rec.jam_riil_pabrik or 0.0) + (rec.jam_riil_luar or 0.0)

    # ════════════════════════════════════════════════════════════
    #  COMPUTE — Finansial Monitoring SBH & SPT
    # ════════════════════════════════════════════════════════════
    @api.depends(
        'tebu_tr_sbh', 'tebu_ts', 'tebu_spt', 'tebu_total',
        'rend_tr', 'rend_ts', 'rend_spt',
        'tetes_ton', 'pct_tetes',
        'periode_id', 'company_id', 'recompute_trigger',
    )
    def _compute_financials(self):
        for rec in self:
            hb = rec._get_harga_biaya()
            par = rec._get_parameter()

            # snapshot konfigurasi
            rec.bagi_hasil_rate = rec.periode_id.bagi_hasil_rate if rec.periode_id else 0.0
            rec.harga_gula = hb.harga_gula if hb else 0.0
            rec.harga_tetes = hb.harga_tetes if hb else 0.0
            rec.pembelian_spt = hb.pembelian_spt if hb else 0.0
            rec.biaya_produksi = hb.biaya_produksi if hb else 0.0
            rec.biaya_laba = hb.biaya_laba if hb else 0.0
            rec.faktor_gula = (par.faktor_gula if par else 1.003) or 1.003
            faktor = rec.faktor_gula

            # ── SBH (basis: TR-SBH + TS) ──
            tebu_sbh = (rec.tebu_tr_sbh or 0.0) + (rec.tebu_ts or 0.0)
            if tebu_sbh:
                rec.rend_sbh = (
                    (rec.tebu_tr_sbh or 0.0) * (rec.rend_tr or 0.0)
                    + (rec.tebu_ts or 0.0) * (rec.rend_ts or 0.0)
                ) / tebu_sbh
            else:
                rec.rend_sbh = 0.0
            rec.sbh_prod_gula = tebu_sbh * rec.rend_sbh * faktor / 100.0
            rec.sbh_prod_tetes = tebu_sbh * (rec.pct_tetes or 0.0) / 100.0
            rec.sbh_gula_milik_pg = rec.sbh_prod_gula - (rec.bagi_hasil_rate * tebu_sbh / 100.0)
            rec.sbh_tetes_milik_pg = rec.sbh_prod_tetes
            rec.sbh_bagi_hasil_rp = rec.bagi_hasil_rate * rec.harga_gula
            if tebu_sbh:
                rec.sbh_pendapatan = (
                    (rec.sbh_gula_milik_pg * rec.harga_gula + rec.sbh_tetes_milik_pg * rec.harga_tetes)
                    / tebu_sbh / 10.0 * 1000.0
                )
            else:
                rec.sbh_pendapatan = 0.0
            rec.sbh_laba_biaya_ku = rec.sbh_pendapatan - rec.biaya_produksi
            rec.sbh_laba_biaya_rp = rec.sbh_laba_biaya_ku * tebu_sbh * 10.0
            rec.sbh_labarugi_ku = rec.sbh_pendapatan - rec.biaya_laba
            rec.sbh_labarugi_rp = rec.sbh_labarugi_ku * tebu_sbh * 10.0
            if tebu_sbh:
                rec.sbh_status = 'laba' if rec.sbh_labarugi_rp >= 0 else 'rugi'
            else:
                rec.sbh_status = False

            # ── SPT (basis: tebu SPT; pabrik membeli tebu) ──
            tebu_spt = rec.tebu_spt or 0.0
            rec.spt_prod_gula = tebu_spt * (rec.rend_spt or 0.0) * faktor / 100.0
            rec.spt_prod_tetes = tebu_spt * (rec.pct_tetes or 0.0) / 100.0
            if tebu_spt:
                rec.spt_pendapatan = (
                    (rec.spt_prod_gula * rec.harga_gula + rec.spt_prod_tetes * rec.harga_tetes)
                    / tebu_spt / 10.0 * 1000.0
                )
            else:
                rec.spt_pendapatan = 0.0
            rec.spt_laba_pembelian = rec.spt_pendapatan - rec.pembelian_spt
            rec.spt_laba_biaya_ku = rec.spt_laba_pembelian - rec.biaya_produksi
            rec.spt_laba_biaya_rp = rec.spt_laba_biaya_ku * tebu_spt * 10.0
            rec.spt_labarugi_ku = rec.spt_laba_pembelian - rec.biaya_laba
            rec.spt_labarugi_rp = rec.spt_labarugi_ku * tebu_spt * 10.0
            if tebu_spt:
                rec.spt_status = 'laba' if rec.spt_labarugi_rp >= 0 else 'rugi'
            else:
                rec.spt_status = False

            # ── Total gabungan ──
            rec.labarugi_total_rp = rec.sbh_labarugi_rp + rec.spt_labarugi_rp

    # ════════════════════════════════════════════════════════════
    #  HELPER — ambil konfigurasi
    # ════════════════════════════════════════════════════════════
    def _get_harga_biaya(self):
        self.ensure_one()
        HB = self.env['ka.giling.harga.biaya']
        if not self.periode_id:
            return HB.browse()
        domain = [('periode_id', '=', self.periode_id.id)]
        if self.company_id:
            hb = HB.search(domain + [('company_id', '=', self.company_id.id)],
                           order='id desc', limit=1)
            if hb:
                return hb
        return HB.search(domain, order='id desc', limit=1)

    def _get_parameter(self):
        self.ensure_one()
        Param = self.env['ka.giling.parameter']
        if self.company_id:
            par = Param.search([('company_id', '=', self.company_id.id)],
                               order='id desc', limit=1)
            if par:
                return par
        return Param.search([], order='id desc', limit=1)

    # ════════════════════════════════════════════════════════════
    #  AGREGASI TEBU dari ka_timbangan
    # ════════════════════════════════════════════════════════════
    def _fill_tebu_from_timbangan(self):
        """Hitung tebu TR-SBH / TS / SPT (Ton) dari ka.timbang.tebu untuk tanggal record ini.
        Klasifikasi memakai register (jenis_register & metode). 1 Ton = 1000 Kg (weight_net)."""
        self.ensure_one()
        res = {'tebu_tr_sbh': 0.0, 'tebu_ts': 0.0, 'tebu_spt': 0.0}
        if not self.date:
            return res
        Timbang = self.env['ka.timbang.tebu'].sudo()
        # "Hari giling" = [D 06:00:00 ; (D+1) 06:00:00) WAKTU PABRIK (WIB).
        # Odoo menyimpan Datetime dalam UTC, maka batas waktu pabrik dikonversi ke UTC.
        # Interval setengah-terbuka agar tidak ada timbangan terlewat/ganda di batas 06:00.
        tz = pytz.timezone(FACTORY_TZ)
        local_start = tz.localize(datetime.combine(self.date, GILING_DAY_START))
        local_next = local_start + timedelta(days=1)            # (D+1) 06:00:00 WIB
        start = local_start.astimezone(pytz.utc).replace(tzinfo=None)
        end = local_next.astimezone(pytz.utc).replace(tzinfo=None)
        domain = [('date_out', '>=', start), ('date_out', '<', end)]
        if 'active' in Timbang._fields:
            domain.append(('active', '=', True))
        if self.company_id and 'company_id' in Timbang._fields:
            domain.append(('company_id', '=', self.company_id.id))

        groups = Timbang.read_group(domain, ['weight_net:sum'], ['register_id'])
        reg_ids = [g['register_id'][0] for g in groups if g.get('register_id')]
        regs = {r.id: r for r in self.env['ka.sita.register'].sudo().browse(reg_ids)}
        for g in groups:
            rid = g['register_id'][0] if g.get('register_id') else False
            ton = (g.get('weight_net') or 0.0) / 1000.0
            reg = regs.get(rid)
            if not reg:
                # register tidak diketahui → default ke TR-SBH
                res['tebu_tr_sbh'] += ton
                continue
            if reg.metode == 'SPT':
                res['tebu_spt'] += ton
            elif reg.jenis_register == 'TS':
                res['tebu_ts'] += ton
            else:  # TR + SBH
                res['tebu_tr_sbh'] += ton
        return res

    def _generate_truk_lines(self):
        """Generate baris Rincian Truk dari ka.timbang.tebu untuk hari giling ini,
        sekaligus menetapkan tebu_tr_sbh/ts/spt = jumlah per kategori dari baris truk
        (satu sumber kebenaran). Dipanggil saat Tarik Timbangan / create / cron."""
        self.ensure_one()
        Truk = self.env['ka.giling.truk'].sudo()
        # bersihkan baris lama
        self.sudo().truk_ids.unlink()
        if not self.date:
            self.tebu_tr_sbh = self.tebu_ts = self.tebu_spt = 0.0
            return

        Timbang = self.env['ka.timbang.tebu'].sudo()
        # Jendela hari giling: [D 06:00:00 ; (D+1) 06:00:00) WIB → konversi ke UTC.
        # Setengah-terbuka: truk yang keluar tepat 06:00:00 besok TIDAK ikut hari ini.
        tz = pytz.timezone(FACTORY_TZ)
        local_start = tz.localize(datetime.combine(self.date, GILING_DAY_START))
        local_next = local_start + timedelta(days=1)
        start = local_start.astimezone(pytz.utc).replace(tzinfo=None)
        end = local_next.astimezone(pytz.utc).replace(tzinfo=None)
        domain = [('date_out', '>=', start), ('date_out', '<', end)]
        if 'active' in Timbang._fields:
            domain.append(('active', '=', True))
        if self.company_id and 'company_id' in Timbang._fields:
            domain.append(('company_id', '=', self.company_id.id))

        recs = Timbang.search(domain, order='date_out asc')
        sums = {'tr_sbh': 0.0, 'ts': 0.0, 'spt': 0.0}
        vals_list = []
        for t in recs:
            reg = t.register_id
            if reg and reg.metode == 'SPT':
                kat = 'spt'
            elif reg and reg.jenis_register == 'TS':
                kat = 'ts'
            else:  # TR + SBH, atau register tak dikenal → default TR-SBH
                kat = 'tr_sbh'
            tebu = (t.weight_net or 0.0) / 1000.0
            sums[kat] += tebu
            vals_list.append({
                'giling_id': self.id,
                'timbang_id': t.id,
                'no_spta': t.no_spta or t.spta_id or '',
                'register_id': reg.id if reg else False,
                'kategori': kat,
                'date_out': t.date_out,
                'tebu_ton': tebu,
                'rend_qc': t.rendemen or 0.0,
            })

        # set tebu header dulu (agar header recompute), baru buat baris (baris ikut config terbaru)
        self.tebu_tr_sbh = sums['tr_sbh']
        self.tebu_ts = sums['ts']
        self.tebu_spt = sums['spt']
        if vals_list:
            Truk.create(vals_list)

    @api.onchange('date', 'company_id')
    def _onchange_date_fill_tebu(self):
        if self.date:
            vals = self._fill_tebu_from_timbangan()
            self.tebu_tr_sbh = vals['tebu_tr_sbh']
            self.tebu_ts = vals['tebu_ts']
            self.tebu_spt = vals['tebu_spt']

    def action_tarik_timbangan(self):
        """Tombol: tarik ulang data tebu + generate Rincian Truk dari timbangan."""
        for rec in self:
            rec._generate_truk_lines()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Data Timbangan Ditarik'),
                'message': _('Tebu tergiling & Rincian Truk diperbarui dari ka_timbangan.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_recompute(self):
        """Tombol: paksa hitung ulang monitoring (mis. setelah ubah harga/parameter)."""
        self.write({'recompute_trigger': fields.Datetime.now()})
        return True

    # ════════════════════════════════════════════════════════════
    #  CREATE — auto gil_ke & auto tarik tebu
    # ════════════════════════════════════════════════════════════
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('gil_ke') and vals.get('date'):
                company_id = vals.get('company_id') or self.env.company.id
                season = self.env['ka.giling.season'].search([
                    ('date_start', '<=', vals['date']),
                    ('date_end', '>=', vals['date']),
                    ('company_id', '=', company_id),
                ], limit=1)
                if season:
                    cnt = self.search_count([('season_id', '=', season.id)])
                    vals['gil_ke'] = cnt + 1
        records = super().create(vals_list)
        if not self.env.context.get('skip_tebu_autofill'):
            for rec in records:
                if rec.date and not (rec.tebu_tr_sbh or rec.tebu_ts or rec.tebu_spt):
                    rec._generate_truk_lines()
        return records

    # ════════════════════════════════════════════════════════════
    #  CRON — sinkron tebu beberapa hari terakhir
    # ════════════════════════════════════════════════════════════
    @api.model
    def _cron_sync_tebu(self, days=3):
        """Tarik ulang tebu dari timbangan untuk N hari terakhir (default 3)."""
        cutoff = fields.Date.today() - timedelta(days=days)
        recs = self.search([('date', '>=', cutoff)])
        for rec in recs:
            rec._generate_truk_lines()
        return True
