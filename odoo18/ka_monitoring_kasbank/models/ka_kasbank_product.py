# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KaKasbankProduct(models.Model):
    """Master Produk Gula — dipakai oleh Persediaan & Penjualan
    (GKP 50Kg, GKP Premium, Ritel 1Kg, Ritel 500g, Setengah Jadi, SIP).
    """
    _name = 'ka.kasbank.product'
    _description = 'Master Produk Gula'
    _order = 'sequence, name'

    name = fields.Char(string='Nama Produk', required=True)
    code = fields.Char(string='Kode')
    category = fields.Selection(
        [('gkp', 'GKP'),
         ('ritel', 'Ritel'),
         ('setengah_jadi', 'Setengah Jadi'),
         ('sip', 'SIP')],
        string='Kategori', required=True, default='gkp')
    satuan = fields.Selection(
        [('ton', 'Ton'), ('kg', 'Kg')],
        string='Satuan Dasar', default='ton',
        help='Satuan acuan: Bulk biasanya Ton, Ritel biasanya Kg.')
    giling_key = fields.Selection(
        [('gkp', 'GKP'), ('gkp_premium', 'GKP-Premium'), ('gula_reject', 'Gula Reject'),
         ('gula_ex2025', 'Gula @50kg ex-2025'), ('produk_rs', 'Produk RS'),
         ('tetes', 'Tetes'), ('ampas', 'Ampas')],
        string='Sumber Produksi Giling',
        help='Kaitkan produk ini ke jenis keluaran di ka_monitoring (Rincian Produksi). '
             'Dipakai wizard "Tarik Produksi" untuk mengisi kolom Produksi/Diolah Persediaan. '
             'Kosongkan bila produk ini tidak berasal langsung dari produksi giling.')
    sequence = fields.Integer(string='Urutan', default=10)
    active = fields.Boolean(string='Aktif', default=True)
    note = fields.Char(string='Keterangan')

    # product_id (product.product) sengaja BELUM ditambahkan —
    # link ke katalog produk Odoo menyusul bila modul product/akuntansi dipakai.
