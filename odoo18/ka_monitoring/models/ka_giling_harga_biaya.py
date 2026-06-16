# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaGilingHargaBiaya(models.Model):
    """Harga & Biaya — harga gula/tetes, biaya produksi, pembelian SPT per periode.
    (Sumber: sheet 'Monitoring SPT' kolom input)."""
    _name = 'ka.giling.harga.biaya'
    _description = 'Harga & Biaya'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'periode_id'
    _order = 'periode_id, id'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company
    )
    periode_id = fields.Many2one(
        'ka.giling.periode', string='Periode', required=True,
        ondelete='cascade', tracking=True
    )
    season_id = fields.Many2one(
        'ka.giling.season', string='Musim',
        related='periode_id.season_id', store=True, readonly=True
    )
    harga_gula = fields.Float(string='Harga Gula (Rp/kg)', digits=(16, 2), tracking=True)
    harga_tetes = fields.Float(string='Harga Tetes (Rp/kg)', digits=(16, 2), tracking=True)
    pembelian_spt = fields.Float(string='Pembelian SPT (Rp/Ku)', digits=(16, 2), tracking=True,
                                 help='Harga beli tebu SPT per kuintal')
    biaya_produksi = fields.Float(string='Biaya Produksi Pabrik (Rp/Ku)', digits=(16, 2), tracking=True)
    biaya_laba = fields.Float(string='Biaya + Laba / Min Margin (Rp/Ku)', digits=(16, 2), tracking=True,
                              help='Biaya produksi + target laba (minimum margin tebu)')
    active = fields.Boolean(default=True)

    def _touch_giling(self):
        """Recompute monitoring hari giling pada periode terkait saat harga/biaya berubah.
        Aman dipanggil sebelum model ka.giling.harian diaktifkan (Fase 4)."""
        if 'ka.giling.harian' not in self.env:
            return
        periode_ids = self.mapped('periode_id').ids
        if not periode_ids:
            return
        gilings = self.env['ka.giling.harian'].search(
            [('periode_id', 'in', periode_ids)])
        if gilings:
            gilings.write({'recompute_trigger': fields.Datetime.now()})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._touch_giling()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._touch_giling()
        return res

    def unlink(self):
        periode_ids = self.mapped('periode_id').ids
        res = super().unlink()
        if periode_ids and 'ka.giling.harian' in self.env:
            gilings = self.env['ka.giling.harian'].search(
                [('periode_id', 'in', periode_ids)])
            if gilings:
                gilings.write({'recompute_trigger': fields.Datetime.now()})
        return res
