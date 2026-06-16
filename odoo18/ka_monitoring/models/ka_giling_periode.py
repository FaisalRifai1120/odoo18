# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaGilingPeriode(models.Model):
    """Periode Tutupan — periode bagi hasil ke petani (sumber: sheet 'Tutupan')."""
    _name = 'ka.giling.periode'
    _description = 'Periode Tutupan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'code'
    _order = 'date_start, code'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company
    )
    season_id = fields.Many2one(
        'ka.giling.season', string='Musim', required=True,
        ondelete='cascade', tracking=True
    )
    code = fields.Char(string='Kode Periode', required=True, tracking=True,
                       help='Mis. "1.A", "2.A"')
    date_start = fields.Date(string='Tanggal Mulai', required=True, tracking=True)
    bagi_hasil_rate = fields.Float(
        string='Bagi Hasil ke Petani (Kg/Ku)', digits=(12, 4), tracking=True,
        help='Tarif gula bagian petani per kuintal tebu'
    )
    active = fields.Boolean(default=True)

    harga_biaya_ids = fields.One2many(
        'ka.giling.harga.biaya', 'periode_id', string='Harga & Biaya')

    _sql_constraints = [
        ('code_season_uniq', 'UNIQUE(code, season_id)',
         'Kode Periode harus unik per Musim!'),
    ]

    def name_get(self):
        result = []
        for rec in self:
            label = rec.code or ''
            if rec.season_id:
                label = f"[{rec.season_id.name}] {label}"
            result.append((rec.id, label))
        return result

    def _touch_giling(self):
        """Recompute monitoring pada hari giling terkait saat bagi hasil berubah.
        Aman dipanggil sebelum model ka.giling.harian diaktifkan (Fase 4)."""
        if 'ka.giling.harian' not in self.env:
            return
        gilings = self.env['ka.giling.harian'].search(
            [('periode_id', 'in', self.ids)])
        if gilings:
            gilings.write({'recompute_trigger': fields.Datetime.now()})

    def write(self, vals):
        res = super().write(vals)
        if 'bagi_hasil_rate' in vals:
            self._touch_giling()
        return res
