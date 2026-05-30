# -*- coding: utf-8 -*-
import logging
import psycopg2
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KaSyncConfig(models.Model):
    _name = 'ka.sync.config'
    _description = 'Konfigurasi Sinkronisasi Database Eksternal'
    _rec_name = 'name'

    name = fields.Char(string='Nama Konfigurasi', required=True, default='Koneksi SITA')
    active = fields.Boolean(default=True)
    db_host = fields.Char(string='Host', required=True, default='localhost')
    db_port = fields.Integer(string='Port', required=True, default=5432)
    db_name = fields.Char(string='Nama Database', required=True)
    db_user = fields.Char(string='Username', required=True)
    db_password = fields.Char(string='Password', required=True, password=True)
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
        self.ensure_one()
        conn = self._get_connection()
        conn.close()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Koneksi Berhasil',
                'message': f'Berhasil terhubung ke {self.db_name} di {self.db_host}:{self.db_port}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sync_manual(self):
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

    def _fetch_from_postgres(self, limit=None):
        """
        Ambil data dari PostgreSQL dan tutup koneksi SEBELUM kembali.
        Return: list of dicts
        """
        conn = None
        try:
            _logger.info('[KA-SITA] ════════════════════════════════════════')
            sync_type = 'MANUAL' if limit else 'CRON'
            _logger.info('[KA-SITA] Sync %s dimulai | Config: %s', sync_type, self.name)
            _logger.debug(
                '[KA-SITA] Menghubungkan ke: %s@%s:%s/%s',
                self.db_user, self.db_host, self.db_port, self.db_name
            )
            conn = self._get_connection()
            _logger.debug('[KA-SITA] ✓ Koneksi database berhasil')
            cur = conn.cursor()

            if limit:
                _logger.debug('[KA-SITA] Query: register | Limit: %d terbaru', limit)
                cur.execute("""
                    SELECT kode, nama, nik, norek, bank, atas_nama
                    FROM public.register
                    WHERE kode IS NOT NULL
                    ORDER BY date_maint DESC NULLS LAST
                    LIMIT %s
                """, (limit,))
            else:
                _logger.debug('[KA-SITA] Query: register | Tanpa limit')
                cur.execute("""
                    SELECT kode, nama, nik, norek, bank, atas_nama
                    FROM public.register
                    WHERE kode IS NOT NULL
                    ORDER BY date_maint DESC NULLS LAST
                """)

            rows = cur.fetchall()
            _logger.debug('[KA-SITA] ✓ Data ditemukan: %d record', len(rows))

            # Konversi ke list of dicts
            result = [
                {
                    'kode':      row[0],
                    'nama':      row[1],
                    'nik':       row[2],
                    'norek':     row[3],
                    'bank':      row[4],
                    'atas_nama': row[5],
                }
                for row in rows
            ]
            return result

        except UserError:
            raise
        except Exception as e:
            _logger.error('[KA-SITA] ✗ Gagal fetch dari PostgreSQL: %s', str(e))
            raise UserError(_('Gagal mengambil data dari PostgreSQL: %s') % str(e))
        finally:
            # Selalu tutup koneksi
            if conn:
                try:
                    conn.close()
                    _logger.debug('[KA-SITA] ✓ Koneksi PostgreSQL ditutup')
                except Exception:
                    pass

    def _do_sync(self, limit=None):
        """
        Core sync logic.
        Koneksi PostgreSQL ditutup SEBELUM operasi ORM dimulai.
        """
        self.ensure_one()
        sync_type = 'MANUAL' if limit else 'CRON'
        start_time = datetime.now()
        count = 0

        # Step 1: Fetch dari PostgreSQL, koneksi langsung ditutup
        rows = self._fetch_from_postgres(limit=limit)
        total_rows = len(rows)

        # Step 2: Proses dengan Odoo ORM (batch processing)
        Register = self.env['ka.sita.register'].sudo().with_context(
            tracking_disable=True,
            mail_notrack=True,
            mail_create_nolog=True,
        )
        count_insert = 0
        count_update = 0

        BATCH_SIZE = 500

        # Ambil semua kode_register yang sudah ada
        existing_keys = {
            r['kode_register']: r['id']
            for r in Register.search_read([], ['kode_register', 'id'])
        }

        vals_to_create = []
        vals_to_update = []  # list of (id, vals)

        _logger.debug('[KA-SITA] Memproses %d record ke Odoo...', total_rows)

        for idx, row in enumerate(rows, start=1):
            kode = row['kode']
            vals = {
                'nama_register': row['nama'] or '',
                'no_ktp':        row['nik'] or '',
                'no_rekening':   row['norek'] or '',
                'nama_bank':     row['bank'] or '',
                'nama_rekening': row['atas_nama'] or '',
            }

            if kode in existing_keys:
                vals_to_update.append((existing_keys[kode], vals))
            else:
                vals['kode_register']  = kode
                vals['jenis_register'] = 'TR'
                vals['metode']         = 'SBH'
                vals['jenis_pembayaran'] = 'Harian'
                vals_to_create.append(vals)

            # Flush batch
            if len(vals_to_create) >= BATCH_SIZE:
                Register.create(vals_to_create)
                count_insert += len(vals_to_create)
                vals_to_create = []

            if len(vals_to_update) >= BATCH_SIZE:
                for rec_id, rec_vals in vals_to_update:
                    Register.browse(rec_id).write(rec_vals)
                count_update += len(vals_to_update)
                vals_to_update = []

            if idx % 500 == 0 or idx == total_rows:
                _logger.debug(
                    '[KA-SITA] Progress [%s]: %d/%d | Insert: %d | Update: %d',
                    sync_type, idx, total_rows,
                    count_insert + len(vals_to_create),
                    count_update + len(vals_to_update)
                )

        # Flush sisa batch
        if vals_to_create:
            Register.create(vals_to_create)
            count_insert += len(vals_to_create)

        if vals_to_update:
            for rec_id, rec_vals in vals_to_update:
                Register.browse(rec_id).write(rec_vals)
            count_update += len(vals_to_update)

        count = count_insert + count_update
        elapsed = (datetime.now() - start_time).total_seconds()
        _logger.debug(
            '[KA-SITA] ✓ Sync %s selesai | Total: %d | Insert: %d | Update: %d | Waktu: %.2fs',
            sync_type, total_rows, count_insert, count_update, elapsed
        )
        _logger.info('[KA-SITA] ════════════════════════════════════════')
        return count

    @api.model
    def cron_sync_register(self):
        configs = self.search([('active', '=', True)], limit=1)
        if not configs:
            _logger.warning('[KA-SITA] Tidak ada konfigurasi aktif, cron dilewati.')
            return
        try:
            count = configs._do_sync(limit=None)
            configs.write({
                'last_sync': fields.Datetime.now(),
                'last_sync_status': 'success',
                'last_sync_message': f'Cron sync berhasil: {count} record diproses.',
            })
        except Exception as e:
            _logger.error('[KA-SITA] ✗ Cron sync GAGAL | Error: %s', str(e))
            configs.write({
                'last_sync': fields.Datetime.now(),
                'last_sync_status': 'failed',
                'last_sync_message': str(e),
            })
