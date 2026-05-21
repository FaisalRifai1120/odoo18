# -*- coding: utf-8 -*-
from odoo import models, fields, api


class KaSitaRegisterRule(models.Model):
    """
    Helper untuk mendapatkan daftar PPL ID yang bisa diakses
    berdasarkan struktur hierarki organisasi.
    """
    _inherit = 'ka.user.profile'

    def _get_bawahan_ppl_ids(self):
        """Rekursif: dapatkan semua PPL di bawah user ini."""
        self.ensure_one()
        if self.role == 'ppl' and self.bagian == 'tanaman':
            return self
        bawahan = self.env['ka.user.profile'].search(
            [('atasan_id', '=', self.id), ('active', '=', True)]
        )
        result = self.env['ka.user.profile']
        for b in bawahan:
            result |= b._get_bawahan_ppl_ids()
        return result
