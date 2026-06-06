# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KaQuotaSpta(models.Model):
    """Quota SPTA harian — dibuat oleh Operator TA, disetujui Kasi TA."""
    _name = 'ka.quota.spta'
    _description = 'Quota SPTA Harian'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'tanggal DESC, name'

    name = fields.Char(
        string='No. Quota', readonly=True, copy=False,
        default='/'
    )
    tanggal = fields.Date(
        string='Tanggal', required=True,
        default=fields.Date.today, tracking=True
    )
    jumlah_quota = fields.Integer(
        string='Jumlah Quota SPTA', required=True,
        tracking=True
    )
    jumlah_terpakai = fields.Integer(
        string='Terpakai', compute='_compute_jumlah_terpakai',
        store=True
    )
    jumlah_sisa = fields.Integer(
        string='Sisa', compute='_compute_jumlah_terpakai',
        store=True
    )
    keterangan = fields.Text(string='Keterangan', tracking=True)
    state = fields.Selection([
        ('draft',    'Draft'),
        ('approved', 'Disetujui'),
        ('cancel',   'Dibatalkan'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many(
        'ka.quota.spta.line', 'quota_id',
        string='Plot per Wilayah'
    )
    spta_ids = fields.One2many(
        'ka.spta', 'quota_id', string='Daftar SPTA'
    )

    create_uid_name = fields.Char(
        string='Dibuat Oleh', compute='_compute_create_uid_name',
        store=False
    )

    def _compute_create_uid_name(self):
        for rec in self:
            rec.create_uid_name = rec.create_uid.name or ''

    @api.depends('line_ids.jumlah_spta', 'line_ids.state')
    def _compute_jumlah_terpakai(self):
        for rec in self:
            terpakai = sum(
                l.jumlah_spta for l in rec.line_ids
                if l.state == 'approved'
            )
            rec.jumlah_terpakai = terpakai
            rec.jumlah_sisa = rec.jumlah_quota - terpakai

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('ka.quota.spta') or '/'
        return super().create(vals_list)

    def action_approve(self):
        """Kasi TA menyetujui quota."""
        self.ensure_one()
        if not self.env.user.has_group('ka_user_management.group_ka_kasi'):
            raise UserError(_('Hanya Kasi TA yang dapat menyetujui Quota SPTA.'))
        if self.jumlah_quota <= 0:
            raise UserError(_('Jumlah quota harus lebih dari 0.'))
        self.write({'state': 'approved'})

    def action_cancel(self):
        """Batalkan quota — hanya Kasi TA atau Admin."""
        self.ensure_one()
        if not (
            self.env.user.has_group('ka_user_management.group_ka_kasi') or
            self.env.user.has_group('ka_user_management.group_ka_admin')
        ):
            raise UserError(_('Hanya Kasi TA atau Administrator yang dapat membatalkan Quota.'))
        if self.state == 'approved':
            raise UserError(_('Quota yang sudah disetujui tidak bisa dibatalkan.'))
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})


class KaQuotaSptaLine(models.Model):
    """Plot quota SPTA ke wilayah/KUD."""
    _name = 'ka.quota.spta.line'
    _description = 'Plot Quota SPTA per Wilayah'
    _inherit = ['mail.thread']
    _rec_name = 'kud_id'
    _order = 'quota_id, kud_id'

    quota_id = fields.Many2one(
        'ka.quota.spta', string='Quota', required=True,
        ondelete='cascade'
    )
    tanggal = fields.Date(
        related='quota_id.tanggal', store=True, readonly=True
    )
    kud_id = fields.Many2one(
        'ka.kud', string='KUD', required=True, ondelete='restrict'
    )
    kota_id = fields.Many2one(
        'ka.wilayah.kota', string='Kota/Kabupaten',
        related='kud_id.kota_id', store=True, readonly=True
    )
    jumlah_spta = fields.Integer(
        string='Jumlah SPTA', required=True, tracking=True
    )
    jumlah_terisi = fields.Integer(
        string='Terisi', compute='_compute_jumlah_terisi', store=True
    )
    jumlah_sisa = fields.Integer(
        string='Sisa', compute='_compute_jumlah_terisi', store=True
    )
    keterangan = fields.Text(string='Keterangan')
    state = fields.Selection([
        ('draft',    'Draft'),
        ('approved', 'Disetujui'),
        ('cancel',   'Dibatalkan'),
    ], string='Status', default='draft', tracking=True)

    spta_ids = fields.One2many(
        'ka.spta', 'quota_line_id', string='SPTA'
    )

    @api.depends('spta_ids', 'spta_ids.state')
    def _compute_jumlah_terisi(self):
        for rec in self:
            terisi = len(rec.spta_ids.filtered(
                lambda s: s.state not in ('cancel',)
            ))
            rec.jumlah_terisi = terisi
            rec.jumlah_sisa = rec.jumlah_spta - terisi

    def write(self, vals):
        """Setelah approved, hanya Admin yang bisa ubah."""
        for rec in self:
            if rec.state == 'approved':
                if not self.env.user.has_group('ka_user_management.group_ka_admin'):
                    raise UserError(_(
                        'Plot wilayah yang sudah disetujui tidak bisa diubah. '
                        'Hubungi Administrator.'
                    ))
        return super().write(vals)

    def action_approve(self):
        """Kasubsi/Kasi TA menyetujui plot wilayah."""
        self.ensure_one()
        if not (
            self.env.user.has_group('ka_user_management.group_ka_kasubsi') or
            self.env.user.has_group('ka_user_management.group_ka_kasi')
        ):
            raise UserError(_('Hanya Kasubsi/Kasi TA yang dapat menyetujui plot wilayah.'))
        if self.quota_id.state != 'approved':
            raise UserError(_('Quota induk harus disetujui terlebih dahulu.'))
        if self.jumlah_spta <= 0:
            raise UserError(_('Jumlah SPTA harus lebih dari 0.'))

        # Cek total plot tidak melebihi quota
        total_plot = sum(
            l.jumlah_spta for l in self.quota_id.line_ids
            if l.state == 'approved' and l.id != self.id
        ) + self.jumlah_spta
        if total_plot > self.quota_id.jumlah_quota:
            raise UserError(_(
                'Total plot (%d) melebihi quota (%d).'
            ) % (total_plot, self.quota_id.jumlah_quota))

        self.write({'state': 'approved'})

    def action_cancel(self):
        self.ensure_one()
        if not (
            self.env.user.has_group('ka_user_management.group_ka_kasi') or
            self.env.user.has_group('ka_user_management.group_ka_kasubsi') or
            self.env.user.has_group('ka_user_management.group_ka_admin')
        ):
            raise UserError(_('Hanya Kasubsi/Kasi TA atau Administrator yang dapat membatalkan plot wilayah.'))
        if self.jumlah_terisi > 0:
            raise UserError(_('Tidak bisa dibatalkan, sudah ada SPTA yang dibuat.'))
        self.write({'state': 'cancel'})
