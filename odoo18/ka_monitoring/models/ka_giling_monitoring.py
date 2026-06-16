# -*- coding: utf-8 -*-
from odoo import models, fields, tools


class KaGilingMonitoringSbh(models.Model):
    """Monitoring SBH (read-only). Proyeksi kolom hasil hitung dari ka.giling.harian."""
    _name = 'ka.giling.monitoring.sbh'
    _description = 'Monitoring SBH'
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    giling_id = fields.Many2one('ka.giling.harian', string='Hari Giling', readonly=True)
    company_id = fields.Many2one('res.company', string='Unit', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    periode_id = fields.Many2one('ka.giling.periode', string='Periode', readonly=True)
    periode_code = fields.Char(string='Kode Periode', readonly=True)

    tebu_sbh = fields.Float(string='Tebu SBH (Ton)', readonly=True)
    tebu_total = fields.Float(string='Total Tebu (Ton)', readonly=True)
    rend_sbh = fields.Float(string='Rend. SBH (%)', readonly=True)
    harga_gula = fields.Float(string='Harga Gula (Rp/kg)', readonly=True)
    harga_tetes = fields.Float(string='Harga Tetes (Rp/kg)', readonly=True)

    prod_gula = fields.Float(string='Produksi Gula (Ton)', readonly=True)
    prod_tetes = fields.Float(string='Produksi Tetes (Ton)', readonly=True)
    gula_milik_pg = fields.Float(string='Gula Milik PG (Ton)', readonly=True)
    tetes_milik_pg = fields.Float(string='Tetes Milik PG (Ton)', readonly=True)
    bagi_hasil_rate = fields.Float(string='Bagi Hasil (Kg/Ku)', readonly=True)
    bagi_hasil_rp = fields.Float(string='Bagi Hasil Gula (Rp/Ku)', readonly=True)

    pendapatan = fields.Float(string='Pendapatan (Rp/Ku)', readonly=True)
    biaya_produksi = fields.Float(string='Biaya Produksi (Rp/Ku)', readonly=True)
    laba_biaya_ku = fields.Float(string='Laba thd Biaya Produksi (Rp/Ku)', readonly=True)
    laba_biaya_rp = fields.Float(string='Laba thd Biaya Produksi (Rp)', readonly=True)
    biaya_laba = fields.Float(string='Biaya + Laba (Rp/Ku)', readonly=True)
    labarugi_ku = fields.Float(string='Laba/Rugi Total (Rp/Ku)', readonly=True)
    labarugi_rp = fields.Float(string='Laba/Rugi Total (Rp)', readonly=True)
    status = fields.Selection([('laba', 'Laba'), ('rugi', 'Rugi')], string='Status', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW %s AS (
                SELECT
                    g.id                                                    AS id,
                    g.id                                                    AS giling_id,
                    g.company_id                                            AS company_id,
                    g.date                                                  AS date,
                    g.periode_id                                            AS periode_id,
                    g.periode_code                                          AS periode_code,
                    (COALESCE(g.tebu_tr_sbh, 0) + COALESCE(g.tebu_ts, 0))   AS tebu_sbh,
                    g.tebu_total                                            AS tebu_total,
                    g.rend_sbh                                              AS rend_sbh,
                    g.harga_gula                                            AS harga_gula,
                    g.harga_tetes                                           AS harga_tetes,
                    g.sbh_prod_gula                                         AS prod_gula,
                    g.sbh_prod_tetes                                        AS prod_tetes,
                    g.sbh_gula_milik_pg                                     AS gula_milik_pg,
                    g.sbh_tetes_milik_pg                                    AS tetes_milik_pg,
                    g.bagi_hasil_rate                                       AS bagi_hasil_rate,
                    g.sbh_bagi_hasil_rp                                     AS bagi_hasil_rp,
                    g.sbh_pendapatan                                        AS pendapatan,
                    g.biaya_produksi                                        AS biaya_produksi,
                    g.sbh_laba_biaya_ku                                     AS laba_biaya_ku,
                    g.sbh_laba_biaya_rp                                     AS laba_biaya_rp,
                    g.biaya_laba                                            AS biaya_laba,
                    g.sbh_labarugi_ku                                       AS labarugi_ku,
                    g.sbh_labarugi_rp                                       AS labarugi_rp,
                    g.sbh_status                                            AS status
                FROM ka_giling_harian g
            )
        """ % self._table)


class KaGilingMonitoringSpt(models.Model):
    """Monitoring SPT (read-only). Proyeksi kolom hasil hitung dari ka.giling.harian."""
    _name = 'ka.giling.monitoring.spt'
    _description = 'Monitoring SPT'
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    giling_id = fields.Many2one('ka.giling.harian', string='Hari Giling', readonly=True)
    company_id = fields.Many2one('res.company', string='Unit', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    periode_id = fields.Many2one('ka.giling.periode', string='Periode', readonly=True)
    periode_code = fields.Char(string='Kode Periode', readonly=True)

    tebu_spt = fields.Float(string='Tebu SPT (Ton)', readonly=True)
    tebu_total = fields.Float(string='Total Tebu (Ton)', readonly=True)
    rend_spt = fields.Float(string='Rend. SPT (%)', readonly=True)
    harga_gula = fields.Float(string='Harga Gula (Rp/kg)', readonly=True)
    harga_tetes = fields.Float(string='Harga Tetes (Rp/kg)', readonly=True)
    pembelian_spt = fields.Float(string='Pembelian SPT (Rp/Ku)', readonly=True)

    prod_gula = fields.Float(string='Produksi Gula (Ton)', readonly=True)
    prod_tetes = fields.Float(string='Produksi Tetes (Ton)', readonly=True)
    pendapatan = fields.Float(string='Pendapatan (Rp/Ku)', readonly=True)
    laba_pembelian = fields.Float(string='Laba Pembelian (Rp/Ku)', readonly=True)
    biaya_produksi = fields.Float(string='Biaya Produksi (Rp/Ku)', readonly=True)
    laba_biaya_ku = fields.Float(string='Laba thd Biaya Produksi (Rp/Ku)', readonly=True)
    laba_biaya_rp = fields.Float(string='Laba thd Biaya Produksi (Rp)', readonly=True)
    biaya_laba = fields.Float(string='Biaya + Laba (Rp/Ku)', readonly=True)
    labarugi_ku = fields.Float(string='Laba/Rugi Total (Rp/Ku)', readonly=True)
    labarugi_rp = fields.Float(string='Laba/Rugi Total (Rp)', readonly=True)
    status = fields.Selection([('laba', 'Laba'), ('rugi', 'Rugi')], string='Status', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW %s AS (
                SELECT
                    g.id                    AS id,
                    g.id                    AS giling_id,
                    g.company_id            AS company_id,
                    g.date                  AS date,
                    g.periode_id            AS periode_id,
                    g.periode_code          AS periode_code,
                    g.tebu_spt              AS tebu_spt,
                    g.tebu_total            AS tebu_total,
                    g.rend_spt              AS rend_spt,
                    g.harga_gula            AS harga_gula,
                    g.harga_tetes           AS harga_tetes,
                    g.pembelian_spt         AS pembelian_spt,
                    g.spt_prod_gula         AS prod_gula,
                    g.spt_prod_tetes        AS prod_tetes,
                    g.spt_pendapatan        AS pendapatan,
                    g.spt_laba_pembelian    AS laba_pembelian,
                    g.biaya_produksi        AS biaya_produksi,
                    g.spt_laba_biaya_ku     AS laba_biaya_ku,
                    g.spt_laba_biaya_rp     AS laba_biaya_rp,
                    g.biaya_laba            AS biaya_laba,
                    g.spt_labarugi_ku       AS labarugi_ku,
                    g.spt_labarugi_rp       AS labarugi_rp,
                    g.spt_status            AS status
                FROM ka_giling_harian g
            )
        """ % self._table)


class KaGilingRekap(models.Model):
    """Rekapitulasi & Dashboard (read-only). Dataset per hari untuk grafik & laba/rugi total."""
    _name = 'ka.giling.rekap'
    _description = 'Rekapitulasi & Dashboard Giling'
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    giling_id = fields.Many2one('ka.giling.harian', string='Hari Giling', readonly=True)
    company_id = fields.Many2one('res.company', string='Unit', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    season_id = fields.Many2one('ka.giling.season', string='Musim', readonly=True)
    periode_id = fields.Many2one('ka.giling.periode', string='Periode', readonly=True)
    gil_ke = fields.Integer(string='Giling ke-', readonly=True)

    tebu_tr_sbh = fields.Float(string='Tebu TR-SBH (Ton)', readonly=True)
    tebu_ts = fields.Float(string='Tebu TS (Ton)', readonly=True)
    tebu_spt = fields.Float(string='Tebu SPT (Ton)', readonly=True)
    tebu_total = fields.Float(string='Total Tebu (Ton)', readonly=True)
    rend_rata = fields.Float(string='Rend. Rata-rata (%)', readonly=True)
    kapasitas_brutto = fields.Float(string='Kapasitas Brutto (TCD)', readonly=True)
    total_produksi = fields.Float(string='Total Produksi Gula (Ton)', readonly=True)
    pct_tetes = fields.Float(string='Tetes % Tebu', readonly=True)

    labarugi_sbh = fields.Float(string='Laba/Rugi SBH (Rp)', readonly=True)
    labarugi_spt = fields.Float(string='Laba/Rugi SPT (Rp)', readonly=True)
    labarugi_total = fields.Float(string='Laba/Rugi Total (Rp)', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW %s AS (
                SELECT
                    g.id                    AS id,
                    g.id                    AS giling_id,
                    g.company_id            AS company_id,
                    g.date                  AS date,
                    g.season_id             AS season_id,
                    g.periode_id            AS periode_id,
                    g.gil_ke                AS gil_ke,
                    g.tebu_tr_sbh           AS tebu_tr_sbh,
                    g.tebu_ts               AS tebu_ts,
                    g.tebu_spt              AS tebu_spt,
                    g.tebu_total            AS tebu_total,
                    g.rend_rata             AS rend_rata,
                    g.kapasitas_brutto      AS kapasitas_brutto,
                    g.total_produksi        AS total_produksi,
                    g.pct_tetes             AS pct_tetes,
                    g.sbh_labarugi_rp       AS labarugi_sbh,
                    g.spt_labarugi_rp       AS labarugi_spt,
                    g.labarugi_total_rp     AS labarugi_total
                FROM ka_giling_harian g
            )
        """ % self._table)
