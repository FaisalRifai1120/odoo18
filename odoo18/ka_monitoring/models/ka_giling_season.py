# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class KaGilingSeason(models.Model):
    """Musim Giling — tahun & rentang tanggal buka/tutup giling."""
    _name = 'ka.giling.season'
    _description = 'Musim Giling'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_start DESC, name DESC'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company
    )
    name = fields.Char(string='Tahun Musim', required=True, tracking=True,
                       help='Mis. "2026"')
    date_start = fields.Date(string='Tanggal Buka Giling', required=True, tracking=True)
    date_end = fields.Date(string='Tanggal Tutup Giling', required=True, tracking=True)
    active = fields.Boolean(default=True)

    periode_ids = fields.One2many('ka.giling.periode', 'season_id', string='Periode Tutupan')
    giling_ids = fields.One2many('ka.giling.harian', 'season_id', string='Hari Giling')

    jumlah_periode = fields.Integer(string='Jml. Periode', compute='_compute_counts')
    jumlah_hari = fields.Integer(string='Jml. Hari Giling', compute='_compute_counts')

    _sql_constraints = [
        ('name_company_uniq', 'UNIQUE(name, company_id)',
         'Tahun Musim harus unik per Unit!'),
    ]

    @api.depends('periode_ids', 'giling_ids')
    def _compute_counts(self):
        for rec in self:
            rec.jumlah_periode = len(rec.periode_ids)
            rec.jumlah_hari = len(rec.giling_ids)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise UserError(_('Tanggal Tutup Giling harus setelah Tanggal Buka Giling.'))

    def action_generate_days(self):
        """Buat record Laporan Harian Giling untuk setiap tanggal dalam musim.
        Tebu TIDAK langsung ditarik (skip_tebu_autofill) agar cepat — gunakan
        tombol 'Tarik Semua Timbangan' setelahnya."""
        self.ensure_one()
        if not (self.date_start and self.date_end):
            raise UserError(_('Isi Tanggal Buka & Tutup Giling terlebih dahulu.'))
        Giling = self.env['ka.giling.harian'].with_context(skip_tebu_autofill=True)
        d = self.date_start
        created = 0
        while d <= self.date_end:
            exists = Giling.search_count([
                ('date', '=', d), ('company_id', '=', self.company_id.id),
            ])
            if not exists:
                Giling.create({'date': d, 'company_id': self.company_id.id})
                created += 1
            d += timedelta(days=1)
        self.action_renumber_giling()
        return self._notify(_('%s hari giling dibuat.') % created)

    def action_renumber_giling(self):
        """Urutkan ulang 'Giling ke-' berdasarkan tanggal."""
        for season in self:
            gilings = self.env['ka.giling.harian'].search(
                [('season_id', '=', season.id)], order='date asc, id asc')
            i = 1
            for g in gilings:
                if g.gil_ke != i:
                    g.gil_ke = i
                i += 1
        return True

    def action_tarik_semua_timbangan(self):
        """Tarik ulang data tebu + Rincian Truk untuk seluruh hari giling musim ini."""
        self.ensure_one()
        gilings = self.env['ka.giling.harian'].search([('season_id', '=', self.id)])
        for g in gilings:
            g._generate_truk_lines()
        return self._notify(_('Data tebu & rincian truk %s hari giling berhasil ditarik ulang.') % len(gilings))

    def action_open_giling(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Hari Giling — %s') % self.name,
            'res_model': 'ka.giling.harian',
            'view_mode': 'list,form',
            'domain': [('season_id', '=', self.id)],
            'context': {'default_season_id': self.id, 'search_default_group_periode': 1},
        }

    def _notify(self, message, title=None, ntype='success'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title or _('Berhasil'),
                'message': message,
                'type': ntype,
                'sticky': False,
            }
        }
