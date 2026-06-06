# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KaSpta(models.Model):
    """SPTA — Surat Perintah Tebang Angkut."""
    _name = 'ka.spta'
    _description = 'SPTA (Surat Perintah Tebang Angkut)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'no_qts'
    _order = 'no_qts DESC'

    # ── Identitas ──────────────────────────────────────────────
    no_qts = fields.Char(
        string='No. QTS', readonly=True, copy=False,
        default='/', index=True, tracking=True,
        help='Nomor Quota Tebang SPTA'
    )
    tanggal = fields.Date(
        string='Tanggal', required=True,
        default=fields.Date.today, tracking=True
    )

    # ── Relasi Quota ───────────────────────────────────────────
    quota_id = fields.Many2one(
        'ka.quota.spta', string='Quota',
        ondelete='restrict', tracking=True
    )
    quota_line_id = fields.Many2one(
        'ka.quota.spta.line', string='Plot Wilayah',
        ondelete='restrict', tracking=True,
        domain="[('quota_id','=',quota_id),('state','=','approved')]"
    )

    # ── Register & Petani ──────────────────────────────────────
    # KUD dari plot wilayah — dipakai sebagai domain filter register
    plot_kud_id = fields.Many2one(
        'ka.kud', string='KUD Plot',
        related='quota_line_id.kud_id',
        store=True, readonly=True
    )
    register_id = fields.Many2one(
        'ka.sita.register', string='Register',
        domain="[('active','=',True), ('kud_id','=',plot_kud_id)]",
        ondelete='restrict', tracking=True
    )
    nama_register_display = fields.Char(
        string='Nama Register',
        related='register_id.nama_register',
        readonly=True
    )
    petani_id = fields.Many2one(
        'ka.petani', string='Petani',
        related='register_id.petani_id',
        store=True, readonly=True
    )
    kud_id = fields.Many2one(
        'ka.kud', string='KUD',
        related='register_id.kud_id',
        store=True, readonly=True
    )
    ppl_id = fields.Many2one(
        'ka.user.profile', string='PPL',
        related='register_id.ppl_id',
        store=True, readonly=True
    )

    # ── Tebang & Angkut ────────────────────────────────────────
    jenis_tebang = fields.Selection([
        ('PG',     'Tebang PG'),
        ('KUD',    'Tebang KUD'),
        ('SENDIRI','Tebang Sendiri'),
    ], string='Jenis Tebang', required=True,
        default='PG', tracking=True
    )
    jenis_truk_id = fields.Many2one(
        'ka.jenis.truk', string='Jenis Truk',
        ondelete='restrict', tracking=True
    )
    jumlah_diberikan = fields.Integer(
        string='Jumlah SPTA Diberikan',
        default=1, tracking=True,
        help='Jumlah SPTA yang diberikan ke petani dari plot wilayah ini'
    )
    quota_sisa = fields.Integer(
        string='Sisa Quota Plot',
        compute='_compute_quota_sisa',
        help='Sisa quota yang tersedia di plot wilayah ini'
    )

    # ── Jadwal ─────────────────────────────────────────────────
    tgl_mulai = fields.Datetime(
        string='Mulai', required=True, tracking=True
    )
    tgl_selesai = fields.Datetime(
        string='Selesai', required=True, tracking=True
    )

    # ── Status ─────────────────────────────────────────────────
    state = fields.Selection([
        ('draft',       'Draft'),
        ('filled',      'Register Terisi'),
        ('approved',    'Disetujui'),
        ('distributed', 'Cetak'),
        ('cancel',      'Dibatalkan'),
    ], string='Status', default='draft', tracking=True)

    # ── Nomor SPTA yang di-generate ───────────────────────────
    nomor_ids = fields.One2many(
        'ka.spta.nomor', 'spta_id', string='Nomor SPTA'
    )
    jumlah_generated = fields.Integer(
        string='Sudah Di-generate',
        compute='_compute_jumlah_generated', store=True
    )

    # ── Cetak ──────────────────────────────────────────────────
    is_printed = fields.Boolean(string='Sudah Dicetak', default=False)
    tgl_cetak = fields.Datetime(string='Tgl. Cetak', readonly=True)

    # ── Notes ──────────────────────────────────────────────────
    notes = fields.Text(string='Catatan')

    # ── Generate No. SPTA ──────────────────────────────────────
    def _generate_nomor_spta_batch(self, tanggal, jumlah):
        """
        Generate sejumlah nomor SPTA sekaligus.
        Format: DDMMNNNN
        DDMM = tanggal & bulan, NNNN = nomor urut (reset tiap hari)
        Return: list of string nomor SPTA
        """
        if isinstance(tanggal, str):
            from datetime import datetime as dt
            tanggal = dt.strptime(tanggal, '%Y-%m-%d').date()

        tgl_str = tanggal.strftime('%d%m')

        # Hitung yang sudah ada hari ini (sekali query)
        existing = self.env['ka.spta.nomor'].search_count([
            ('tanggal', '=', tanggal),
        ])

        result = []
        for i in range(jumlah):
            urut = str(existing + i + 1).zfill(4)
            result.append(f"{tgl_str}{urut}")
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('no_qts', '/') == '/':
                vals['no_qts'] = self.env['ir.sequence'].next_by_code('ka.spta.qts') or '/'
        return super().create(vals_list)

    @api.depends('nomor_ids')
    def _compute_jumlah_generated(self):
        for rec in self:
            rec.jumlah_generated = len(rec.nomor_ids)

    @api.depends('quota_line_id', 'quota_line_id.jumlah_spta', 'jumlah_diberikan')
    def _compute_quota_sisa(self):
        """Sisa = quota plot - total jumlah_diberikan semua SPTA di plot ini."""
        for rec in self:
            if rec.quota_line_id:
                total_approved = sum(
                    s.jumlah_diberikan for s in rec.quota_line_id.spta_ids
                    if s.state not in ('cancel',) and s.id != rec._origin.id
                )
                rec.quota_sisa = rec.quota_line_id.jumlah_spta - total_approved - rec.jumlah_diberikan
            else:
                rec.quota_sisa = 0

    def _get_allowed_kud_ids(self):
        """Helper: dapatkan IDs KUD yang diperbolehkan berdasarkan quota."""
        self.ensure_one()
        if self.quota_line_id:
            return self.quota_line_id.kud_id.ids
        elif self.quota_id:
            approved_lines = self.quota_id.line_ids.filtered(
                lambda l: l.state == 'approved'
            )
            return approved_lines.mapped('kud_id').ids
        return []

    @api.onchange('quota_id')
    def _onchange_quota_id(self):
        """Saat quota berubah, reset quota_line_id dan update domain-nya."""
        self.quota_line_id = False
        self.register_id = False
        domain_line = []
        if self.quota_id:
            domain_line = [
                ('quota_id', '=', self.quota_id.id),
                ('state', '=', 'approved'),
            ]
        return {
            'domain': {
                'quota_line_id': domain_line,
                'register_id': [('active', '=', True)],
            }
        }

    @api.onchange('quota_line_id')
    def _onchange_quota_line_id_register(self):
        """Filter register berdasarkan KUD dari plot wilayah yang dipilih."""
        if self.quota_line_id:
            kud_id = self.quota_line_id.kud_id.id
            # Reset register jika tidak sesuai KUD
            if self.register_id and self.register_id.kud_id.id != kud_id:
                self.register_id = False
            return {
                'domain': {
                    'register_id': [
                        ('active', '=', True),
                        ('kud_id', '=', kud_id),
                        ('nama_register', '!=', False),
                        ('nama_register', '!=', ''),
                    ]
                }
            }
        return {
            'domain': {
                'register_id': [
                    ('active', '=', True),
                    ('nama_register', '!=', False),
                    ('nama_register', '!=', ''),
                ]
            }
        }

    @api.onchange('quota_id')
    def _onchange_quota_id_register(self):
        """Reset register saat quota berubah."""
        self.register_id = False
        return {
            'domain': {
                'register_id': [
                    ('active', '=', True),
                    ('nama_register', '!=', False),
                    ('nama_register', '!=', ''),
                ]
            }
        }

    @api.onchange('register_id')
    def _onchange_register_id(self):
        if self.register_id:
            self.jenis_truk_id = False

    @api.onchange('quota_line_id')
    def _onchange_quota_line_id(self):
        if self.quota_line_id:
            self.quota_id = self.quota_line_id.quota_id

    def action_fill_register(self):
        """Operator TA mengisi register ke SPTA."""
        self.ensure_one()
        if not self.register_id:
            raise UserError(_('Harap isi Register terlebih dahulu.'))
        if not self.jenis_truk_id:
            raise UserError(_('Harap isi Jenis Truk.'))
        if not self.tgl_mulai or not self.tgl_selesai:
            raise UserError(_('Harap isi Tanggal Mulai dan Selesai.'))
        if self.tgl_selesai <= self.tgl_mulai:
            raise UserError(_('Tanggal Selesai harus setelah Tanggal Mulai.'))
        if self.jumlah_diberikan <= 0:
            raise UserError(_('Jumlah SPTA yang diberikan harus lebih dari 0.'))
        if self.quota_line_id and self.jumlah_diberikan > self.quota_line_id.jumlah_sisa:
            raise UserError(_(
                'Jumlah yang diberikan (%d) melebihi sisa quota plot (%d).'
            ) % (self.jumlah_diberikan, self.quota_line_id.jumlah_sisa))
        self.write({'state': 'filled'})

    def action_approve(self):
        """Kasubsi TA menyetujui SPTA dan generate nomor SPTA."""
        self.ensure_one()
        if not (
            self.env.user.has_group('ka_user_management.group_ka_kasubsi') or
            self.env.user.has_group('ka_user_management.group_ka_kasi')
        ):
            raise UserError(_('Hanya Kasubsi/Kasi TA yang dapat menyetujui SPTA.'))
        if self.state != 'filled':
            raise UserError(_('SPTA harus dalam status Register Terisi untuk disetujui.'))
        if self.jumlah_diberikan <= 0:
            raise UserError(_('Jumlah SPTA yang diberikan harus lebih dari 0.'))
        if self.quota_line_id and self.jumlah_diberikan > self.quota_line_id.jumlah_sisa:
            raise UserError(_(
                'Jumlah yang diberikan (%d) melebihi sisa quota plot (%d).'
            ) % (self.jumlah_diberikan, self.quota_line_id.jumlah_sisa))

        # Generate nomor SPTA sejumlah jumlah_diberikan (batch, tidak ada duplikat)
        nomor_list = self._generate_nomor_spta_batch(self.tanggal, self.jumlah_diberikan)
        nomor_vals = [
            {'spta_id': self.id, 'no_spta': no}
            for no in nomor_list
        ]
        self.env['ka.spta.nomor'].create(nomor_vals)
        self.write({'state': 'approved'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'SPTA Disetujui',
                'message': f'{self.jumlah_diberikan} nomor SPTA berhasil di-generate.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_distribute(self):
        """Distribusikan SPTA ke petani."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('SPTA harus disetujui sebelum Cetak.'))
        self.write({
            'state': 'distributed',
            'is_printed': True,
            'tgl_cetak': fields.Datetime.now(),
        })

    def action_cancel(self):
        """Batalkan SPTA — hanya Kasi TA atau Admin."""
        self.ensure_one()
        if not (
            self.env.user.has_group('ka_user_management.group_ka_kasi') or
            self.env.user.has_group('ka_user_management.group_ka_admin')
        ):
            raise UserError(_('Hanya Kasi TA atau Administrator yang dapat membatalkan SPTA.'))
        if self.state == 'distributed':
            raise UserError(_('SPTA yang sudah Cetak tidak bisa dibatalkan.'))
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.ensure_one()
        if self.state not in ('filled', 'cancel'):
            raise UserError(_('Hanya SPTA berstatus Terisi atau Batal yang bisa direset.'))
        self.write({'state': 'draft'})

    def action_preview_spta(self):
        """Tampilkan preview SPTA di layar."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Preview SPTA {self.no_qts}',
            'res_model': 'ka.spta',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('ka_sita.view_ka_spta_print_form').id,
            'target': 'new',
        }

    def action_lihat_nomor_spta(self):
        """Lihat daftar nomor SPTA yang di-generate."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Nomor SPTA — {self.no_qts} ({self.jumlah_generated} nomor)',
            'res_model': 'ka.spta.nomor',
            'view_mode': 'list',
            'domain': [('spta_id', '=', self.id)],
            'context': {'default_spta_id': self.id},
            'target': 'new',
        }
