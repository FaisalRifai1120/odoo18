# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KaRelaksasi(models.Model):
    """
    Master Relaksasi — aturan pengurang rafaksi berdasarkan digit register.
    Per-periode. Yang terakhir dibuat menang saat overlap.
    """
    _name = 'ka.relaksasi'
    _description = 'Relaksasi Rafaksi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date DESC'

    name = fields.Char(
        string='No. Relaksasi', readonly=True, copy=False,
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
        help='Aturan berlaku untuk timbang dengan waktu <= waktu ini (default jam 06:00:00)'
    )
    keterangan = fields.Text(string='Keterangan')

    state = fields.Selection([
        ('active', 'Aktif'),
        ('cancel', 'Dibatalkan'),
    ], string='Status', default='active', tracking=True)

    line_ids = fields.One2many(
        'ka.relaksasi.line', 'relaksasi_id', string='Detail Aturan Digit'
    )
    line_count = fields.Integer(
        string='Jumlah Aturan', compute='_compute_line_count'
    )

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('ka.relaksasi') or '/'
        return super().create(vals_list)

    def action_cancel(self):
        """Batalkan relaksasi (tetap tampil untuk history)."""
        self.ensure_one()
        if not (
            self.env.user.has_group('ka_user_management.group_ka_closing') or
            self.env.user.has_group('ka_user_management.group_ka_admin')
        ):
            raise UserError(_('Anda tidak memiliki akses untuk membatalkan relaksasi.'))
        self.write({'state': 'cancel'})

    def action_set_active(self):
        self.ensure_one()
        self.write({'state': 'active'})

    def unlink(self):
        raise UserError(_(
            'Record Relaksasi tidak dapat dihapus untuk menjaga history. '
            'Gunakan tombol Batalkan.'
        ))

    @api.model
    def get_relaksasi_for_register(self, register_code, waktu_timbang, company_id):
        """
        Hitung nilai relaksasi (%) untuk sebuah register.

        Param:
            register_code : kode register (string)
            waktu_timbang : datetime timbang (date_out)
            company_id    : id company

        Logika:
        1. Cari relaksasi aktif untuk company, filter tgl_berlaku >= waktu_timbang.
        2. Jika tidak ada yang masih berlaku → pakai yang TERAKHIR dibuat.
        3. Dari relaksasi terpilih, cek semua line: match digit register.
        4. Jika beberapa line match → pakai relaksasi TERBESAR.

        Return: float (persentase relaksasi) atau None jika tidak ada match.
        """
        if not register_code:
            return None

        Relaksasi = self.sudo()
        # 1. Cari yang masih berlaku
        domain_base = [
            ('company_id', '=', company_id),
            ('state', '=', 'active'),
        ]
        berlaku = Relaksasi.search(
            domain_base + [('tgl_berlaku', '>=', waktu_timbang)],
            order='create_date DESC', limit=1
        )
        # 2. Fallback: pakai yang terakhir dibuat
        if not berlaku:
            berlaku = Relaksasi.search(
                domain_base, order='create_date DESC', limit=1
            )
        if not berlaku:
            return None

        # 3 & 4. Cek line, ambil relaksasi terbesar yang match
        nilai_terbesar = None
        for line in berlaku.line_ids:
            pos = line.posisi_digit
            if pos < 1 or pos > len(register_code):
                continue
            digit_register = register_code[pos - 1]
            if str(digit_register) == str(line.nilai_digit):
                if nilai_terbesar is None or line.nilai_relaksasi > nilai_terbesar:
                    nilai_terbesar = line.nilai_relaksasi

        return nilai_terbesar


class KaRelaksasiLine(models.Model):
    """Detail aturan relaksasi per digit."""
    _name = 'ka.relaksasi.line'
    _description = 'Detail Aturan Relaksasi'
    _order = 'posisi_digit, nilai_digit'

    relaksasi_id = fields.Many2one(
        'ka.relaksasi', string='Relaksasi', required=True, ondelete='cascade'
    )
    company_id = fields.Many2one(
        'res.company', related='relaksasi_id.company_id',
        store=True, index=True
    )
    posisi_digit = fields.Integer(
        string='Posisi Digit', required=True,
        help='Posisi karakter ke-berapa pada kode register (mulai dari 1)'
    )
    nilai_digit = fields.Char(
        string='Nilai Digit', required=True, size=2,
        help='Nilai karakter pada posisi tersebut (angka/huruf)'
    )
    nilai_relaksasi = fields.Float(
        string='Relaksasi (%)', required=True, digits=(5, 2),
        help='Persentase relaksasi. Rafaksi akan menjadi sebesar persentase ini dari rafaksi asli.'
    )
    keterangan = fields.Char(string='Keterangan')
