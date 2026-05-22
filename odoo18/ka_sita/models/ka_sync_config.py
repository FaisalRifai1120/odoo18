# -*- coding: utf-8 -*-
import logging
import psycopg2
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KaSyncConfig(models.Model):
    """Konfigurasi koneksi database PostgreSQL eksternal untuk sinkronisasi."""
    _name = 'ka.sync.config'
    _description = 'Konfigurasi Sinkronisasi Database Eksternal'
    _rec_name = 'name'

    name = fields.Char(string='Nama Konfigurasi', required=True, default='Koneksi SITA')
    active = fields.Boolean(default=True)

    # ── Koneksi ────────────────────────────────────────────────
    db_host = fields.Char(string='Host', required=True, default='localhost')
    db_port = fields.Integer(string='Port', required=True, default=5432)
    db_name = fields.Char(string='Nama Database', required=True)
    db_user = fields.Char(string='Username', required=True)
    db_password = fields.Char(string='Password', required=True, password=True)

    # ── Status ─────────────────────────────────────────────────
    last_sync = fields.Datetime(string='Terakhir Sync', readonly=True)
    last_sync_status = fields.Selection([
        ('success', 'Berhasil'),
        ('failed',  'Gagal'),
    ], string='Status Terakhir', readonly=True)
    last_sync_message = fields.Text(string='Pesan Terakhir', readonly=True)
    total_synced = fields.Integer(string='Total Record Ter-sync', readonly=True)

    def _get_connection(self):
        """Buat koneksi ke database eksternal."""
        self.ensure_one()
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password,
                connect_timeout=10,
            )
            return conn
        except Exception as e:
            raise UserError(_('Gagal koneksi ke database: %s') % str(e))

    def action_test_connection(self):
        """Test koneksi ke database eksternal."""
        self.ensure_one()
        conn = self._get_connection()
        conn.close()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Koneksi Berhasil',
                'message': f'Berhasil terhubung ke database {self.db_name} di {self.db_host}:{self.db_port}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sync_manual(self):
        """Sync manual: ambil 10 register terbaru berdasarkan date_maint."""
        self.ensure_one()
        count = self._do_sync(limit=10)
        self.write({
            'last_sync': fields.Datetime.now(),
            'last_sync_status': 'success',
            'last_sync_message': f'Sync manual berhasil: {count} register diproses.',
            'total_synced': self.total_synced + count,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Manual Berhasil',
                'message': f'{count} register berhasil disinkronisasi.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sync_all(self):
        """Sync semua register dari database eksternal."""
        self.ensure_one()
        count = self._do_sync(limit=None)
        self.write({
            'last_sync': fields.Datetime.now(),
            'last_sync_status': 'success',
            'last_sync_message': f'Sync semua berhasil: {count} register diproses.',
            'total_synced': self.total_synced + count,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Semua Berhasil',
                'message': f'{count} register berhasil disinkronisasi.',
                'type': 'success',
                'sticky': False,
            }
        }

    def _do_sync(self, limit=None):
        """
        Core sync logic.
        - limit=10   → manual (10 terbaru by date_maint)
        - limit=None → cron (semua)
        """
        self.ensure_one()
        conn = None
        count = 0
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            if limit:
                query = """
                    SELECT kode, nama, nik, norek, bank, atas_nama
                    FROM public.register
                    WHERE kode IS NOT NULL
                    ORDER BY date_maint DESC NULLS LAST
                    LIMIT %s
                """
                cur.execute(query, (limit,))
            else:
                query = """
                    SELECT kode, nama, nik, norek, bank, atas_nama
                    FROM public.register
                    WHERE kode IS NOT NULL
                    ORDER BY date_maint DESC NULLS LAST
                """
                cur.execute(query)

            rows = cur.fetchall()
            Register = self.env['ka.sita.register'].sudo()

            for row in rows:
                kode, nama, nik, norek, bank, atas_nama = row

                # Bersihkan nilai None
                vals = {
                    'nama_register': nama or '',
                    'no_ktp':        nik or '',
                    'no_rekening':   norek or '',
                    'nama_bank':     bank or '',
                    'nama_rekening': atas_nama or '',
                }

                # Cek apakah sudah ada berdasarkan kode
                existing = Register.search(
                    [('kode_register', '=', kode)], limit=1
                )
                if existing:
                    # Update jika ada perubahan
                    existing.write(vals)
                else:
                    # Insert baru
                    vals['kode_register'] = kode
                    # jenis_register & metode wajib di model, set default
                    vals['jenis_register'] = 'TR'
                    vals['metode'] = 'SBH'
                    vals['jenis_pembayaran'] = 'Harian'
                    Register.create(vals)
                count += 1

            conn.close()
            _logger.info('KA SITA Sync: %d register diproses.', count)

        except UserError:
            raise
        except Exception as e:
            if conn:
                conn.close()
            self.write({
                'last_sync': fields.Datetime.now(),
                'last_sync_status': 'failed',
                'last_sync_message': str(e),
            })
            _logger.error('KA SITA Sync error: %s', str(e))
            raise UserError(_('Sync gagal: %s') % str(e))

        return count

    @api.model
    def cron_sync_register(self):
        """Dipanggil oleh cron job tiap 1 menit."""
        configs = self.search([('active', '=', True)], limit=1)
        if not configs:
            _logger.warning('KA SITA Sync: Tidak ada konfigurasi aktif.')
            return
        try:
            configs._do_sync(limit=None)
            configs.write({
                'last_sync': fields.Datetime.now(),
                'last_sync_status': 'success',
                'last_sync_message': 'Cron sync berhasil.',
            })
        except Exception as e:
            _logger.error('KA SITA Cron Sync error: %s', str(e))
