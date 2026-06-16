# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaGilingParameter(models.Model):
    """Parameter Global — konstanta proses (faktor gula, FR, WR, dll)."""
    _name = 'ka.giling.parameter'
    _description = 'Parameter Giling'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'id desc'

    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True, index=True,
        default=lambda self: self.env.company
    )
    name = fields.Char(string='Nama Set Parameter', required=True, default='Parameter Default')
    faktor_gula = fields.Float(string='Faktor Konversi Gula', digits=(12, 4),
                               default=1.003, tracking=True, help='Konstanta, mis. 1.003')
    fr = fields.Float(string='Faktor Rendemen (FR)', digits=(12, 4),
                      default=0.7, tracking=True, help='Konstanta, mis. 0.7')
    wr = fields.Float(string='Faktor WR', digits=(12, 4),
                      default=0.97, tracking=True, help='Konstanta, mis. 0.97')
    brix_tetes_puteran = fields.Float(string='% Brix Tetes Puteran', digits=(12, 4), tracking=True)
    kristal_tetes_standar = fields.Float(string='Kristal Tetes Standar', digits=(12, 4), tracking=True)
    active = fields.Boolean(default=True)

    def _touch_giling(self):
        """Parameter global → recompute seluruh hari giling pada company yang sama.
        Aman dipanggil sebelum model ka.giling.harian diaktifkan (Fase 4)."""
        if 'ka.giling.harian' not in self.env:
            return
        for rec in self:
            gilings = self.env['ka.giling.harian'].search(
                [('company_id', '=', rec.company_id.id)])
            if gilings:
                gilings.write({'recompute_trigger': fields.Datetime.now()})

    def write(self, vals):
        res = super().write(vals)
        touch_fields = {'faktor_gula', 'fr', 'wr'}
        if touch_fields & set(vals.keys()):
            self._touch_giling()
        return res
