# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class KaLaporanHarian(models.Model):
    """Rekap timbang harian — aggregasi per tanggal & register."""
    _name = 'ka.laporan.harian'
    _description = 'Laporan Harian Timbang Tebu'
    _auto = False  # View-based model
    _rec_name = 'tanggal'
    _order = 'tanggal DESC, register'

    company_id    = fields.Many2one('res.company', string='Unit/Company', readonly=True)
    tanggal       = fields.Date(string='Tanggal', readonly=True)
    register      = fields.Char(string='Kode Register', readonly=True)
    register_id   = fields.Many2one('ka.sita.register', string='Register', readonly=True)
    nama_register = fields.Char(string='Nama Register', readonly=True)
    petani_id     = fields.Many2one('ka.petani', string='Petani', readonly=True)
    ppl_id        = fields.Many2one('ka.user.profile', string='PPL', readonly=True)
    jumlah_ritase = fields.Integer(string='Ritase', readonly=True)
    total_bruto   = fields.Float(string='Total Bruto (Kg)', digits=(12, 2), readonly=True)
    total_netto   = fields.Float(string='Total Netto (Kg)', digits=(12, 2), readonly=True)
    total_netto_kw= fields.Float(string='Total Netto (Kw)', digits=(12, 4), readonly=True)
    total_rafaksi = fields.Float(string='Total Rafaksi', digits=(12, 4), readonly=True)
    total_bobot   = fields.Float(string='Total Bobot Tebu', digits=(12, 4), readonly=True)

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS ka_laporan_harian CASCADE;
            CREATE OR REPLACE VIEW ka_laporan_harian AS
            SELECT
                ROW_NUMBER() OVER ()            AS id,
                DATE(t.date_out)                AS tanggal,
                t.company_id                    AS company_id,
                t.register                      AS register,
                t.register_id                   AS register_id,
                COALESCE(r.nama_register, t.register) AS nama_register,
                t.petani_id                     AS petani_id,
                r.ppl_id                        AS ppl_id,
                COUNT(*)                        AS jumlah_ritase,
                SUM(t.weight_in)                AS total_bruto,
                SUM(t.weight_net)               AS total_netto,
                SUM(t.weight_kw)                AS total_netto_kw,
                SUM(t.rafaksi)                  AS total_rafaksi,
                SUM(t.bobot_tebu)               AS total_bobot
            FROM ka_timbang_tebu t
            LEFT JOIN ka_sita_register r ON r.id = t.register_id
            WHERE t.active = true
            GROUP BY
                DATE(t.date_out),
                t.company_id,
                t.register,
                t.register_id,
                r.nama_register,
                t.petani_id,
                r.ppl_id
        """)


class KaLaporanRegister(models.Model):
    """Rekap akumulasi per register — semua periode."""
    _name = 'ka.laporan.register'
    _description = 'Laporan Rekap per Register'
    _auto = False
    _rec_name = 'register'
    _order = 'register'

    company_id    = fields.Many2one('res.company', string='Unit/Company', readonly=True)
    register      = fields.Char(string='Kode Register', readonly=True)
    register_id   = fields.Many2one('ka.sita.register', string='Register', readonly=True)
    nama_register = fields.Char(string='Nama Register', readonly=True)
    petani_id     = fields.Many2one('ka.petani', string='Petani', readonly=True)
    ppl_id        = fields.Many2one('ka.user.profile', string='PPL', readonly=True)
    kud_id        = fields.Many2one('ka.kud', string='KUD', readonly=True)
    jumlah_ritase = fields.Integer(string='Total Ritase', readonly=True)
    total_bruto   = fields.Float(string='Total Bruto (Kg)', digits=(12, 2), readonly=True)
    total_netto   = fields.Float(string='Total Netto (Kg)', digits=(12, 2), readonly=True)
    total_netto_kw= fields.Float(string='Total Netto (Kw)', digits=(12, 4), readonly=True)
    total_rafaksi = fields.Float(string='Total Rafaksi', digits=(12, 4), readonly=True)
    total_bobot   = fields.Float(string='Total Bobot Tebu', digits=(12, 4), readonly=True)
    tgl_pertama   = fields.Datetime(string='Tgl. Timbang Pertama', readonly=True)
    tgl_terakhir  = fields.Datetime(string='Tgl. Timbang Terakhir', readonly=True)

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS ka_laporan_register CASCADE;
            CREATE OR REPLACE VIEW ka_laporan_register AS
            SELECT
                ROW_NUMBER() OVER ()            AS id,
                t.company_id                    AS company_id,
                t.register                      AS register,
                t.register_id                   AS register_id,
                COALESCE(r.nama_register, t.register) AS nama_register,
                t.petani_id                     AS petani_id,
                r.ppl_id                        AS ppl_id,
                r.kud_id                        AS kud_id,
                COUNT(*)                        AS jumlah_ritase,
                SUM(t.weight_in)                AS total_bruto,
                SUM(t.weight_net)               AS total_netto,
                SUM(t.weight_kw)                AS total_netto_kw,
                SUM(t.rafaksi)                  AS total_rafaksi,
                SUM(t.bobot_tebu)               AS total_bobot,
                MIN(t.date_out)                 AS tgl_pertama,
                MAX(t.date_out)                 AS tgl_terakhir
            FROM ka_timbang_tebu t
            LEFT JOIN ka_sita_register r ON r.id = t.register_id
            WHERE t.active = true
            GROUP BY
                t.company_id,
                t.register,
                t.register_id,
                r.nama_register,
                t.petani_id,
                r.ppl_id,
                r.kud_id
        """)


class KaLaporanPpl(models.Model):
    """Rekap per PPL — total semua register di bawah PPL."""
    _name = 'ka.laporan.ppl'
    _description = 'Laporan Rekap per PPL'
    _auto = False
    _rec_name = 'ppl_id'
    _order = 'ppl_id'

    company_id    = fields.Many2one('res.company', string='Unit/Company', readonly=True)
    ppl_id        = fields.Many2one('ka.user.profile', string='PPL', readonly=True)
    jumlah_register = fields.Integer(string='Jml. Register', readonly=True)
    jumlah_ritase = fields.Integer(string='Total Ritase', readonly=True)
    total_netto   = fields.Float(string='Total Netto (Kg)', digits=(12, 2), readonly=True)
    total_netto_kw= fields.Float(string='Total Netto (Kw)', digits=(12, 4), readonly=True)
    total_bobot   = fields.Float(string='Total Bobot Tebu', digits=(12, 4), readonly=True)
    tgl_pertama   = fields.Datetime(string='Tgl. Pertama', readonly=True)
    tgl_terakhir  = fields.Datetime(string='Tgl. Terakhir', readonly=True)

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS ka_laporan_ppl CASCADE;
            CREATE OR REPLACE VIEW ka_laporan_ppl AS
            SELECT
                ROW_NUMBER() OVER ()            AS id,
                t.company_id                    AS company_id,
                r.ppl_id                        AS ppl_id,
                COUNT(DISTINCT t.register_id)   AS jumlah_register,
                COUNT(*)                        AS jumlah_ritase,
                SUM(t.weight_net)               AS total_netto,
                SUM(t.weight_kw)                AS total_netto_kw,
                SUM(t.bobot_tebu)               AS total_bobot,
                MIN(t.date_out)                 AS tgl_pertama,
                MAX(t.date_out)                 AS tgl_terakhir
            FROM ka_timbang_tebu t
            LEFT JOIN ka_sita_register r ON r.id = t.register_id
            WHERE t.active = true
              AND r.ppl_id IS NOT NULL
            GROUP BY t.company_id, r.ppl_id
        """)


class KaLaporanDetail(models.Model):
    """Laporan detail — wrapper ka.timbang.tebu dengan filter tambahan."""
    _name = 'ka.laporan.detail'
    _description = 'Laporan Detail Timbang Tebu'
    _auto = False
    _rec_name = 'spta_id'
    _order = 'date_out DESC'

    company_id    = fields.Many2one('res.company', string='Unit/Company', readonly=True)
    spta_id       = fields.Char(string='Nomor Timbangan', readonly=True)
    no_spta       = fields.Char(string='No. SPTA', readonly=True)
    kd_antrian    = fields.Char(string='Nomor Antrian', readonly=True)
    register      = fields.Char(string='Kode Register', readonly=True)
    register_id   = fields.Many2one('ka.sita.register', string='Register', readonly=True)
    nama_register = fields.Char(string='Nama Register', readonly=True)
    petani_id     = fields.Many2one('ka.petani', string='Petani', readonly=True)
    ppl_id        = fields.Many2one('ka.user.profile', string='PPL', readonly=True)
    kud_id        = fields.Many2one('ka.kud', string='KUD', readonly=True)
    truck_id      = fields.Char(string='No. Polisi', readonly=True)
    weight_in     = fields.Float(string='Masuk (Kg)', digits=(10, 2), readonly=True)
    weight_out    = fields.Float(string='Keluar (Kg)', digits=(10, 2), readonly=True)
    weight_net    = fields.Float(string='Netto (Kg)', digits=(10, 2), readonly=True)
    weight_kw     = fields.Float(string='Netto (Kw)', digits=(10, 4), readonly=True)
    rafaksi       = fields.Float(string='Rafaksi', digits=(10, 2), readonly=True)
    bobot_tebu    = fields.Float(string='Bobot Tebu', digits=(10, 4), readonly=True)
    rendemen      = fields.Float(string='Rendemen', digits=(10, 4), readonly=True)
    mbs_id        = fields.Many2one('ka.mbs', string='MBS', readonly=True)
    varietas      = fields.Char(string='Varietas', readonly=True)
    jenis_tebu    = fields.Char(string='Jenis Tebu', readonly=True)
    date_in       = fields.Datetime(string='Tgl. Masuk', readonly=True)
    date_out      = fields.Datetime(string='Tgl. Keluar', readonly=True)

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS ka_laporan_detail CASCADE;
            CREATE OR REPLACE VIEW ka_laporan_detail AS
            SELECT
                t.id,
                t.company_id,
                t.spta_id,
                t.no_spta,
                t.kd_antrian,
                t.register,
                t.register_id,
                COALESCE(r.nama_register, t.register) AS nama_register,
                t.petani_id,
                r.ppl_id        AS ppl_id,
                r.kud_id        AS kud_id,
                t.truck_id,
                t.weight_in,
                t.weight_out,
                t.weight_net,
                t.weight_kw,
                t.rafaksi,
                t.bobot_tebu,
                t.rendemen,
                t.mbs_id,
                t.varietas,
                t.jenis_tebu,
                t.date_in,
                t.date_out
            FROM ka_timbang_tebu t
            LEFT JOIN ka_sita_register r ON r.id = t.register_id
            WHERE t.active = true
        """)
