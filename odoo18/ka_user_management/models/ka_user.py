# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class KaUserProfile(models.Model):
    _name = 'ka.user.profile'
    _description = 'Profil User KA'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ── Identitas ──────────────────────────────────────────────
    user_id = fields.Many2one(
        'res.users', string='User Odoo', required=True,
        ondelete='cascade', tracking=True,
        domain=[('share', '=', False)]
    )
    name = fields.Char(
        string='Nama Lengkap', required=True, tracking=True
    )
    nip = fields.Char(
        string='NIP', tracking=True
    )
    employee_code = fields.Char(
        string='Kode Pegawai', tracking=True
    )
    phone = fields.Char(string='No. Telepon', tracking=True)
    email = fields.Char(
        string='Email',
        related='user_id.email', store=True, readonly=False
    )

    # ── Jabatan / Peran ────────────────────────────────────────
    role = fields.Selection([
        ('ppl',       'PPL (Penyuluh Pertanian Lapangan)'),
        ('kasubsi',   'KASUBSI (Kepala Sub Seksi)'),
        ('kasi',      'KASI (Kepala Seksi)'),
        ('kabag',     'KABAG (Kepala Bagian)'),
        ('operator',  'Operator'),
        ('admin',     'Administrator'),
    ], string='Jabatan / Peran', required=True, tracking=True)

    # ── Struktur Atasan ────────────────────────────────────────
    atasan_id = fields.Many2one(
        'ka.user.profile', string='Atasan Langsung',
        domain="[('role', 'in', ['kasubsi','kasi','kabag','admin'])]",
        tracking=True
    )

    # ── Status ─────────────────────────────────────────────────
    active = fields.Boolean(default=True, tracking=True)
    state = fields.Selection([
        ('active',   'Aktif'),
        ('inactive', 'Tidak Aktif'),
    ], string='Status', default='active', tracking=True)

    # ── Computed ───────────────────────────────────────────────
    role_label = fields.Char(
        string='Label Jabatan', compute='_compute_role_label', store=True
    )

    @api.depends('role')
    def _compute_role_label(self):
        role_map = {
            'ppl':      'PPL',
            'kasubsi':  'KASUBSI',
            'kasi':     'KASI',
            'kabag':    'KABAG',
            'operator': 'Operator',
            'admin':    'Administrator',
        }
        for rec in self:
            rec.role_label = role_map.get(rec.role, '')

    # ── Constraint ────────────────────────────────────────────
    _sql_constraints = [
        ('user_id_uniq', 'unique(user_id)',
         'Satu akun Odoo hanya boleh memiliki satu profil KA!'),
        ('employee_code_uniq', 'UNIQUE(employee_code)',
         'Kode Pegawai harus unik!'),
    ]

    @api.constrains('role', 'atasan_id')
    def _check_atasan_role(self):
        """PPL wajib memiliki atasan."""
        for rec in self:
            if rec.role == 'ppl' and not rec.atasan_id:
                raise ValidationError(
                    _('PPL harus memiliki Atasan Langsung (KASUBSI/KASI/KABAG).')
                )

    # ── Sync groups Odoo ──────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._sync_odoo_groups()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'role' in vals:
            self._sync_odoo_groups()
        return res

    def _sync_odoo_groups(self):
        """Sinkronisasi grup Odoo berdasarkan peran."""
        group_map = {
            'admin':    'ka_user_management.group_ka_admin',
            'operator': 'ka_user_management.group_ka_operator',
            'kabag':    'ka_user_management.group_ka_kabag',
            'kasi':     'ka_user_management.group_ka_kasi',
            'kasubsi':  'ka_user_management.group_ka_kasubsi',
            'ppl':      'ka_user_management.group_ka_ppl',
        }
        all_groups = list(group_map.values())
        for rec in self:
            user = rec.user_id
            # Hapus semua grup KA dulu
            for xml_id in all_groups:
                try:
                    grp = self.env.ref(xml_id)
                    if user in grp.users:
                        grp.write({'users': [(3, user.id)]})
                except Exception:
                    pass
            # Tambahkan grup sesuai peran
            target_xml = group_map.get(rec.role)
            if target_xml:
                try:
                    grp = self.env.ref(target_xml)
                    grp.write({'users': [(4, user.id)]})
                except Exception:
                    pass

    def action_set_inactive(self):
        self.write({'state': 'inactive', 'active': False})

    def action_set_active(self):
        self.write({'state': 'active', 'active': True})
