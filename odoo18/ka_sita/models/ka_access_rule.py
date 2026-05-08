# -*- coding: utf-8 -*-
from odoo import models, fields, api


class KaSitaRegisterRule(models.Model):
    """
    Helper untuk mendapatkan daftar PPL ID yang bisa diakses
    berdasarkan struktur hierarki organisasi.
    """
    _inherit = 'ka.user.profile'

    def _get_bawahan_ppl_ids(self):
        """
        Rekursif: dapatkan semua PPL di bawah user ini.
        PPL → langsung return diri sendiri (jika role=ppl)
        KASUBSI/KASI/KABAG → cari semua bawahan rekursif sampai PPL
        """
        self.ensure_one()
        if self.role == 'ppl':
            return self

        # Cari semua bawahan langsung
        bawahan = self.env['ka.user.profile'].search(
            [('atasan_id', '=', self.id)]
        )
        result = self.env['ka.user.profile']
        for b in bawahan:
            result |= b._get_bawahan_ppl_ids()
        return result


class KaSitaRegisterAccess(models.Model):
    _inherit = 'ka.sita.register'

    @api.model
    def _get_accessible_ppl_ids(self):
        """Dapatkan list PPL ID yang boleh diakses user saat ini."""
        user_profile = self.env['ka.user.profile'].search(
            [('user_id', '=', self.env.uid)], limit=1
        )
        if not user_profile:
            return []

        if user_profile.role == 'ppl':
            return [user_profile.id]

        if user_profile.role in ['kasubsi', 'kasi', 'kabag']:
            ppl_records = user_profile._get_bawahan_ppl_ids()
            return ppl_records.ids

        # Operator & Admin: return False = semua
        return False

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        """Override search untuk filter berdasarkan hak akses hierarki."""
        domain = self._apply_hierarchy_domain(domain)
        return super().search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        domain = self._apply_hierarchy_domain(domain)
        return super()._search(domain, offset=offset, limit=limit, order=order,
                               access_rights_uid=access_rights_uid)

    @api.model
    def _apply_hierarchy_domain(self, domain):
        """Tambahkan filter hierarki ke domain jika bukan admin/operator."""
        # Skip untuk admin dan superuser
        if self.env.user._is_admin():
            return domain
        if self.env.user.has_group('ka_user_management.group_ka_admin'):
            return domain
        if self.env.user.has_group('ka_user_management.group_ka_operator'):
            return domain

        ppl_ids = self._get_accessible_ppl_ids()
        if ppl_ids is False:
            return domain
        if not ppl_ids:
            # Tidak ada PPL yang bisa diakses → return domain yang pasti kosong
            return domain + [('id', '=', 0)]

        return domain + [('ppl_id', 'in', ppl_ids)]
