# -*- coding: utf-8 -*-
import base64
import io
import math
import logging
from datetime import datetime, time
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def floor2(value):
    """Pembulatan ke bawah 2 desimal. Contoh: 0.058 -> 0.05"""
    if not value:
        return 0.0
    return math.floor(float(value) * 100) / 100.0


def floor0(value):
    """Pembulatan ke bawah ke integer. Contoh: 9950.7 -> 9950"""
    if not value:
        return 0
    return int(math.floor(float(value)))


class KaNtp(models.Model):
    """
    NTP — Nota Tebu Petani.
    Tahap 4a: rekap PER TRUK (belum agregat per register).
    """
    _name = 'ka.ntp'
    _description = 'Nota Tebu Petani'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date DESC'

    name = fields.Char(
        string='No. NTP', readonly=True, copy=False,
        default='/', index=True
    )
    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True,
        default=lambda self: self.env.company, index=True
    )
    tanggal_pembuatan = fields.Date(
        string='Tanggal Pembuatan', required=True,
        default=fields.Date.today, tracking=True
    )
    tgl_awal = fields.Datetime(
        string='Tanggal Awal', required=True, tracking=True,
        help='Default jam 06:00:00'
    )
    tgl_akhir = fields.Datetime(
        string='Tanggal Akhir', required=True, tracking=True,
        help='Default jam 05:59:59'
    )
    periode = fields.Char(string='Periode', tracking=True)

    jenis_kelompok = fields.Selection([
        ('jenis_register', 'Jenis Register (TR/TS)'),
        ('metode',         'Metode (SBH/SPT)'),
        ('digit',          'Per Digit Register'),
    ], string='Jenis Pengelompokan', default='jenis_register', tracking=True)

    # Filter opsional berdasarkan jenis
    filter_jenis_register = fields.Selection([
        ('TR', 'TR'),
        ('TS', 'TS'),
    ], string='Filter Jenis Register')
    filter_metode = fields.Selection([
        ('SBH', 'SBH'),
        ('SPT', 'SPT'),
    ], string='Filter Metode')
    filter_digit_posisi = fields.Integer(string='Posisi Digit Filter')
    filter_digit_nilai = fields.Char(string='Nilai Digit Filter', size=2)

    state = fields.Selection([
        ('draft',  'Draft'),
        ('proses', 'Proses'),
        ('done',   'Selesai'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many('ka.ntp.line', 'ntp_id', string='Detail per Truk')
    line_count = fields.Integer(string='Jml Truk', compute='_compute_totals')

    total_netto       = fields.Float(string='Total Netto', compute='_compute_totals', digits=(16, 2))
    total_netto_relaksasi = fields.Float(string='Total Netto Relaksasi', compute='_compute_totals', digits=(16, 2))
    total_gula        = fields.Integer(string='Total Gula', compute='_compute_totals')
    total_rupiah      = fields.Float(string='Total Rupiah', compute='_compute_totals', digits=(16, 2))

    # Status import (penanda override)
    has_import_relaksasi = fields.Boolean(string='Ada Import Relaksasi', default=False)
    has_import_bagihasil = fields.Boolean(string='Ada Import Bagi Hasil', default=False)

    # Upload fields
    upload_relaksasi_file = fields.Binary(string='File Relaksasi (.xlsx)')
    upload_relaksasi_filename = fields.Char(string='Nama File Relaksasi')
    upload_bagihasil_file = fields.Binary(string='File Bagi Hasil (.xlsx)')
    upload_bagihasil_filename = fields.Char(string='Nama File Bagi Hasil')

    @api.depends('line_ids', 'line_ids.netto', 'line_ids.netto_relaksasi',
                 'line_ids.gula', 'line_ids.rupiah')
    def _compute_totals(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.total_netto = sum(rec.line_ids.mapped('netto'))
            rec.total_netto_relaksasi = sum(rec.line_ids.mapped('netto_relaksasi'))
            rec.total_gula = sum(rec.line_ids.mapped('gula'))
            rec.total_rupiah = sum(rec.line_ids.mapped('rupiah'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('ka.ntp') or '/'
            # Default jam awal 06:00:00 dan akhir 05:59:59 jika hanya tanggal
            if vals.get('tgl_awal') and isinstance(vals['tgl_awal'], str) and len(vals['tgl_awal']) == 10:
                vals['tgl_awal'] = vals['tgl_awal'] + ' 06:00:00'
        return super().create(vals_list)

    # ─────────────────────────────────────────────────────────
    #  TOMBOL: REPROSES
    # ─────────────────────────────────────────────────────────
    def action_reproses(self):
        """
        Tarik ulang data dari ka.timbang.tebu (rentang tgl), hitung per truk:
        rafaksi_relaksasi, netto_relaksasi, gula, rupiah.

        Sumber aturan:
          - Relaksasi & Bagi Hasil dari import (jika ada), else dari menu.
        """
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('NTP yang sudah Selesai tidak bisa di-reproses.'))
        if not self.tgl_awal or not self.tgl_akhir:
            raise UserError(_('Harap isi Tanggal Awal dan Tanggal Akhir.'))

        company_id = self.company_id.id
        ctx = dict(tracking_disable=True, mail_notrack=True, mail_create_nolog=True)

        # 1. Ambil data timbang dalam rentang
        Timbang = self.env['ka.timbang.tebu'].sudo()
        domain = [
            ('company_id', '=', company_id),
            ('date_out', '>=', self.tgl_awal),
            ('date_out', '<=', self.tgl_akhir),
        ]
        # Filter opsional berdasarkan jenis
        if self.jenis_kelompok == 'jenis_register' and self.filter_jenis_register:
            domain.append(('register_id.jenis_register', '=', self.filter_jenis_register))
        elif self.jenis_kelompok == 'metode' and self.filter_metode:
            domain.append(('register_id.metode', '=', self.filter_metode))

        timbang_recs = Timbang.search(domain)

        # Filter per-digit (dilakukan di Python karena karakter ke-N)
        if self.jenis_kelompok == 'digit' and self.filter_digit_posisi and self.filter_digit_nilai:
            pos = self.filter_digit_posisi
            nilai = str(self.filter_digit_nilai)
            timbang_recs = timbang_recs.filtered(
                lambda t: t.register and len(t.register) >= pos
                and str(t.register[pos - 1]) == nilai
            )

        if not timbang_recs:
            raise UserError(_('Tidak ada data timbang dalam rentang tanggal & filter ini.'))

        # 2. Ambil ketentuan & relaksasi aktif (untuk fallback non-import)
        Ketentuan = self.env['ka.ketentuan']
        Relaksasi = self.env['ka.relaksasi']

        # Hapus lines lama
        self.line_ids.unlink()

        # 3. Cache import override (kalau ada)
        import_relaksasi = {}  # register -> persentase
        import_bagihasil = {}  # register -> bagi_hasil
        if self.has_import_relaksasi:
            for l in self.env['ka.ntp.import.relaksasi'].search([('ntp_id', '=', self.id)]):
                import_relaksasi[l.register] = l.persentase
        if self.has_import_bagihasil:
            for l in self.env['ka.ntp.import.bagihasil'].search([('ntp_id', '=', self.id)]):
                import_bagihasil[l.register] = l.bagi_hasil

        Line = self.env['ka.ntp.line'].with_context(**ctx)
        vals_list = []

        for t in timbang_recs:
            register_code = t.register or ''
            waktu = t.date_out or self.tgl_akhir
            bruto = t.weight_kw or 0.0          # weight_kw = bruto (Netto Kw sebelum rafaksi)
            bobot_tebu = t.bobot_tebu or 0.0    # bobot_tebu = bruto - rafaksi asli
            rafaksi_asli = t.rafaksi or 0.0

            # ── Relaksasi ──
            persen_relaksasi = None
            if register_code in import_relaksasi:
                persen_relaksasi = import_relaksasi[register_code]
            else:
                persen_relaksasi = Relaksasi.get_relaksasi_for_register(
                    register_code, waktu, company_id
                )

            if rafaksi_asli > 0 and persen_relaksasi is not None:
                # rafaksi relaksasi = rafaksi asli x persentase
                rafaksi_relaksasi = floor2(rafaksi_asli * (persen_relaksasi / 100.0))
                # netto relaksasi = BRUTO - rafaksi relaksasi
                netto_relaksasi = floor2(bruto - rafaksi_relaksasi)
            else:
                # tidak ada relaksasi → pakai bobot_tebu (bruto - rafaksi asli)
                rafaksi_relaksasi = rafaksi_asli
                netto_relaksasi = bobot_tebu if rafaksi_asli > 0 else bruto

            # ── Bagi Hasil ──
            if register_code in import_bagihasil:
                bagi_hasil = import_bagihasil[register_code]
            else:
                ket = Ketentuan.get_ketentuan_aktif(waktu, company_id)
                bagi_hasil = ket.get_bagi_hasil_for_register(register_code) if ket else 0.0
                harga_gula = ket.harga_gula if ket else 0.0

            # Harga gula dari ketentuan aktif
            ket_for_harga = Ketentuan.get_ketentuan_aktif(waktu, company_id)
            harga_gula = ket_for_harga.harga_gula if ket_for_harga else 0.0

            # ── Hitung gula & rupiah ──
            gula = floor0(netto_relaksasi * bagi_hasil)       # integer
            rupiah = floor2(gula * harga_gula)                # 2 desimal

            vals_list.append({
                'ntp_id':            self.id,
                'timbang_id':        t.id,
                'no_timbang':        t.spta_id,
                'no_spta':           t.no_spta,
                'kd_antrian':        t.kd_antrian,
                'register':          register_code,
                'nama_register':     t.nama_register,
                'petani_id':         t.petani_id.id if t.petani_id else False,
                'date_out':          t.date_out,
                'netto':             bruto,
                'bobot_tebu':        bobot_tebu,
                'rafaksi_asli':      rafaksi_asli,
                'persen_relaksasi':  persen_relaksasi or 0.0,
                'rafaksi_relaksasi': rafaksi_relaksasi,
                'netto_relaksasi':   netto_relaksasi,
                'bagi_hasil':        bagi_hasil,
                'harga_gula':        harga_gula,
                'gula':              gula,
                'rupiah':            rupiah,
            })

        Line.create(vals_list)
        _logger.info('[KA-NTP] Reproses %s: %d truk diproses.', self.name, len(vals_list))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Reproses Selesai',
                'message': f'{len(vals_list)} data truk berhasil diproses.',
                'type': 'success',
                'sticky': False,
            }
        }

    # ─────────────────────────────────────────────────────────
    #  TOMBOL: IMPORT RELAKSASI
    # ─────────────────────────────────────────────────────────
    def action_import_relaksasi(self):
        self.ensure_one()
        if not self.upload_relaksasi_file:
            raise UserError(_('Harap pilih file Excel relaksasi terlebih dahulu.'))
        rows = self._read_xlsx(self.upload_relaksasi_file)

        self.env['ka.ntp.import.relaksasi'].search([('ntp_id', '=', self.id)]).unlink()
        vals_list = []
        for register, nilai in rows:
            vals_list.append({
                'ntp_id': self.id,
                'register': register,
                'persentase': nilai,
            })
        if vals_list:
            self.env['ka.ntp.import.relaksasi'].create(vals_list)

        self.write({
            'has_import_relaksasi': True,
            'upload_relaksasi_file': False,
            'upload_relaksasi_filename': False,
            'state': 'proses',
        })
        return self._notif(f'{len(vals_list)} relaksasi diimpor. Klik Reproses untuk menerapkan.')

    # ─────────────────────────────────────────────────────────
    #  TOMBOL: IMPORT BAGI HASIL
    # ─────────────────────────────────────────────────────────
    def action_import_bagihasil(self):
        self.ensure_one()
        if not self.upload_bagihasil_file:
            raise UserError(_('Harap pilih file Excel bagi hasil terlebih dahulu.'))
        rows = self._read_xlsx(self.upload_bagihasil_file)

        self.env['ka.ntp.import.bagihasil'].search([('ntp_id', '=', self.id)]).unlink()
        vals_list = []
        for register, nilai in rows:
            vals_list.append({
                'ntp_id': self.id,
                'register': register,
                'bagi_hasil': nilai,
            })
        if vals_list:
            self.env['ka.ntp.import.bagihasil'].create(vals_list)

        self.write({
            'has_import_bagihasil': True,
            'upload_bagihasil_file': False,
            'upload_bagihasil_filename': False,
            'state': 'proses',
        })
        return self._notif(f'{len(vals_list)} bagi hasil diimpor. Klik Reproses untuk menerapkan.')

    def _read_xlsx(self, file_b64):
        """Baca xlsx → list of (register, nilai_float). Skip header baris 1."""
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise UserError(_('Library openpyxl belum terpasang di server.'))
        try:
            data = base64.b64decode(file_b64)
            wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            ws = wb.active
        except Exception as e:
            raise UserError(_('Gagal membaca file Excel: %s') % str(e))

        result = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or row[0] is None:
                continue
            register = str(row[0]).strip()
            if not register:
                continue
            try:
                nilai = float(row[1]) if row[1] is not None else 0.0
            except (ValueError, TypeError):
                continue
            result.append((register, nilai))
        return result

    def _notif(self, msg, kind='success'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Info', 'message': msg, 'type': kind, 'sticky': False},
        }

    def action_set_done(self):
        self.ensure_one()
        if not self.env.user.has_group('ka_user_management.group_ka_admin'):
            raise UserError(_('Hanya Administrator yang dapat menyelesaikan NTP.'))
        self.write({'state': 'done'})

    def action_set_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})


class KaNtpLine(models.Model):
    """Detail NTP per truk."""
    _name = 'ka.ntp.line'
    _description = 'Detail NTP per Truk'
    _order = 'date_out, register'

    ntp_id = fields.Many2one('ka.ntp', string='NTP', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='ntp_id.company_id', store=True, index=True)
    timbang_id = fields.Many2one('ka.timbang.tebu', string='Data Timbang', ondelete='set null')

    no_timbang = fields.Char(string='No. Timbang')
    no_spta    = fields.Char(string='No. SPTA')
    kd_antrian = fields.Char(string='No. Antrian')
    register   = fields.Char(string='Register', index=True)
    nama_register = fields.Char(string='Nama Register')
    petani_id  = fields.Many2one('ka.petani', string='Petani')
    date_out   = fields.Datetime(string='Tgl. Keluar')

    netto             = fields.Float(string='Bruto (Kw)', digits=(16, 2))
    bobot_tebu        = fields.Float(string='Bobot Tebu', digits=(16, 2))
    rafaksi_asli      = fields.Float(string='Rafaksi Asli', digits=(16, 2))
    persen_relaksasi  = fields.Float(string='Relaksasi (%)', digits=(5, 2))
    rafaksi_relaksasi = fields.Float(string='Rafaksi Relaksasi', digits=(16, 2))
    netto_relaksasi   = fields.Float(string='Netto Relaksasi', digits=(16, 2))
    bagi_hasil        = fields.Float(string='Bagi Hasil', digits=(10, 4))
    harga_gula        = fields.Float(string='Harga Gula', digits=(16, 2))
    gula              = fields.Integer(string='Gula')
    rupiah            = fields.Float(string='Rupiah', digits=(16, 2))


class KaNtpImportRelaksasi(models.Model):
    """Staging import relaksasi per NTP."""
    _name = 'ka.ntp.import.relaksasi'
    _description = 'Import Relaksasi NTP'

    ntp_id = fields.Many2one('ka.ntp', required=True, ondelete='cascade')
    register = fields.Char(string='Register', required=True, index=True)
    persentase = fields.Float(string='Relaksasi (%)', digits=(5, 2))


class KaNtpImportBagihasil(models.Model):
    """Staging import bagi hasil per NTP."""
    _name = 'ka.ntp.import.bagihasil'
    _description = 'Import Bagi Hasil NTP'

    ntp_id = fields.Many2one('ka.ntp', required=True, ondelete='cascade')
    register = fields.Char(string='Register', required=True, index=True)
    bagi_hasil = fields.Float(string='Bagi Hasil', digits=(10, 4))
