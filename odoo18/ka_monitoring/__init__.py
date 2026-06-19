# -*- coding: utf-8 -*-
from . import models


def _init_produksi_lines(env):
    """Post-init: bangun Rincian Produksi untuk seluruh Laporan Harian Giling
    yang sudah ada, agar menu Produksi Gula langsung terisi setelah upgrade."""
    recs = env['ka.giling.harian'].search([])
    for rec in recs:
        if not rec.produksi_ids:
            rec._sync_produksi_lines()
