# -*- coding: utf-8 -*-
import base64
import io
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KaKetentuan(models.Model):
    """
    Master Ketentuan — harga, faktor rendemen, bagi hasil.
    Per-periode. Yang terakhir dibuat menang saat overlap.
    """
    _name = 'ka.ketentuan'
    _description = 'Ketentuan Bagi Hasil'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date DESC'

    name = fields.Char(
        string='No. Ketentuan', readonly=True, copy=False,
        default='/', index=True
    )
    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True,
        default=lambda self: self.env.company, index=True
    )
    tanggal = fields.Date(
        string='Tanggal Dibuat', required=True,
        default=fields.Date.today, tracking=True
    )
    tgl_berlaku = fields.Datetime(
        string='Berlaku Hingga', required=True, tracking=True,
        help='Ketentuan berlaku untuk timbang dengan waktu <= waktu ini (default jam 06:00:00)'
    )

    # ── Harga ──────────────────────────────────────────────────
    harga_gula  = fields.Float(string='Harga Gula', digits=(16, 2), tracking=True)
    harga_tetes = fields.Float(string='Harga Tetes', digits=(16, 2), tracking=True)

    # ── Faktor Rendemen ────────────────────────────────────────
    faktor_gula     = fields.Float(string='Faktor Rendemen Gula', digits=(10, 4), tracking=True)
    faktor_tetes    = fields.Float(string='Faktor Rendemen Tetes', digits=(10, 4), tracking=True)
    faktor_bh_tetes = fields.Float(string='Faktor B.H Tetes', digits=(10, 4), tracking=True)
    faktor_nira     = fields.Float(string='Faktor Rendemen Nira', digits=(10, 4), tracking=True)

    # ── Bagi Hasil ─────────────────────────────────────────────
    bagi_hasil_default = fields.Float(
        string='Bagi Hasil Default', digits=(10, 4), tracking=True,
        help='Dipakai untuk register yang tidak ada di list bagi hasil.'
    )

    keterangan = fields.Text(string='Keterangan')

    state = fields.Selection([
        ('active', 'Aktif'),
        ('cancel', 'Dibatalkan'),
    ], string='Status', default='active', tracking=True)

    line_ids = fields.One2many(
        'ka.ketentuan.line', 'ketentuan_id', string='Bagi Hasil per Register'
    )
    line_count = fields.Integer(string='Jml Register', compute='_compute_line_count')

    # ── Upload ─────────────────────────────────────────────────
    upload_file = fields.Binary(string='File Excel (.xlsx)')
    upload_filename = fields.Char(string='Nama File')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('ka.ketentuan') or '/'
        return super().create(vals_list)

    def action_cancel(self):
        self.ensure_one()
        if not (
            self.env.user.has_group('ka_user_management.group_ka_closing') or
            self.env.user.has_group('ka_user_management.group_ka_admin')
        ):
            raise UserError(_('Anda tidak memiliki akses untuk membatalkan ketentuan.'))
        self.write({'state': 'cancel'})

    def action_set_active(self):
        self.ensure_one()
        self.write({'state': 'active'})

    def unlink(self):
        raise UserError(_(
            'Record Ketentuan tidak dapat dihapus untuk menjaga history. '
            'Gunakan tombol Batalkan.'
        ))

    def action_import_bagihasil(self):
        """Import list bagi hasil per register dari Excel."""
        self.ensure_one()
        if not self.upload_file:
            raise UserError(_('Harap pilih file Excel terlebih dahulu.'))

        try:
            from openpyxl import load_workbook
        except ImportError:
            raise UserError(_('Library openpyxl belum terpasang di server. Hubungi Administrator.'))

        try:
            data = base64.b64decode(self.upload_file)
            wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            ws = wb.active
        except Exception as e:
            raise UserError(_('Gagal membaca file Excel: %s') % str(e))

        # Hapus line lama
        self.line_ids.unlink()

        Line = self.env['ka.ketentuan.line']
        vals_list = []
        skipped = 0
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or row[0] is None:
                continue
            register = str(row[0]).strip()
            if not register:
                continue
            try:
                bagi_hasil = float(row[1]) if row[1] is not None else 0.0
            except (ValueError, TypeError):
                skipped += 1
                continue
            vals_list.append({
                'ketentuan_id': self.id,
                'register': register,
                'bagi_hasil': bagi_hasil,
            })

        if vals_list:
            Line.create(vals_list)

        msg = f'{len(vals_list)} register berhasil diimpor.'
        if skipped:
            msg += f' {skipped} baris dilewati (format tidak valid).'

        self.write({'upload_file': False, 'upload_filename': False})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Selesai',
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def get_ketentuan_aktif(self, waktu_timbang, company_id):
        """
        Ambil ketentuan yang berlaku untuk waktu timbang tertentu.
        Logika sama dengan relaksasi: filter tgl_berlaku, fallback terakhir dibuat.
        Return: record ka.ketentuan atau None.
        """
        domain_base = [
            ('company_id', '=', company_id),
            ('state', '=', 'active'),
        ]
        ket = self.sudo().search(
            domain_base + [('tgl_berlaku', '>=', waktu_timbang)],
            order='create_date DESC', limit=1
        )
        if not ket:
            ket = self.sudo().search(domain_base, order='create_date DESC', limit=1)
        return ket or None

    def get_bagi_hasil_for_register(self, register_code):
        """Ambil BH untuk register: dari list jika ada, else default."""
        self.ensure_one()
        line = self.line_ids.filtered(lambda l: l.register == register_code)
        if line:
            return line[0].bagi_hasil
        return self.bagi_hasil_default


class KaKetentuanLine(models.Model):
    """Bagi hasil per register (dari upload Excel)."""
    _name = 'ka.ketentuan.line'
    _description = 'Bagi Hasil per Register'
    _order = 'register'

    ketentuan_id = fields.Many2one(
        'ka.ketentuan', string='Ketentuan', required=True, ondelete='cascade'
    )
    company_id = fields.Many2one(
        'res.company', related='ketentuan_id.company_id',
        store=True, index=True
    )
    register = fields.Char(string='Register', required=True, index=True)
    bagi_hasil = fields.Float(string='Bagi Hasil', digits=(10, 4), required=True)
