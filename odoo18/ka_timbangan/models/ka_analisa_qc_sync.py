# -*- coding: utf-8 -*-
import logging
import psycopg2
import datetime as _dt
from datetime import timedelta

TZ_OFFSET = timedelta(hours=14)  # 7 jam konversi + 7 jam kompensasi display Odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CRON_SYNC_FROM_YEAR = _dt.date.today().year
TZ_OFFSET = timedelta(hours=14)  # 7 jam konversi + 7 jam kompensasi display Odoo


class KaAnalisaQcSync(models.Model):
    """Sinkronisasi data Analisa QC dari PostgreSQL."""
    _name = 'ka.analisa.qc.sync'
    _description = 'Sinkronisasi Analisa QC'
    _rec_name = 'name'

    name = fields.Char(
        string='Nama', required=True,
        default='Sinkronisasi Analisa QC'
    )
    company_id = fields.Many2one(
        'res.company', string='Unit/Company', required=True,
        default=lambda self: self.env.company, index=True
    )
    active = fields.Boolean(default=True)
    sync_config_id = fields.Many2one(
        'ka.sync.config', string='Konfigurasi Koneksi',
        required=True, ondelete='restrict'
    )
    date_from = fields.Date(string='Tanggal Dari')
    date_to   = fields.Date(string='Tanggal Sampai')

    last_sync         = fields.Datetime(string='Terakhir Sync', readonly=True)
    last_sync_status  = fields.Selection([
        ('success', 'Berhasil'),
        ('failed',  'Gagal'),
    ], string='Status Terakhir', readonly=True)
    last_sync_message = fields.Text(string='Pesan Terakhir', readonly=True)
    total_synced      = fields.Integer(string='Total Record Ter-sync', readonly=True)

    def action_sync_manual(self):
        """Sync manual dengan filter rentang tanggal created_at."""
        self.ensure_one()
        if not self.date_from or not self.date_to:
            raise UserError(_('Harap isi Tanggal Dari dan Tanggal Sampai.'))
        if self.date_from > self.date_to:
            raise UserError(_('Tanggal Dari tidak boleh lebih besar dari Tanggal Sampai.'))

        _logger.info('[KA-QC] Sync MANUAL | %s s/d %s', self.date_from, self.date_to)
        count = self._do_sync(date_from=self.date_from, date_to=self.date_to)
        self.write({
            'last_sync':         fields.Datetime.now(),
            'last_sync_status':  'success',
            'last_sync_message': f'Sync manual: {count} record diproses ({self.date_from} s/d {self.date_to}).',
            'total_synced':      self.total_synced + count,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   'Sync Manual Berhasil',
                'message': f'{count} data analisa QC berhasil disinkronisasi.',
                'type':    'success',
                'sticky':  False,
            }
        }

    def _fetch_from_postgres(self, date_from=None, date_to=None, cron_mode=False):
        """Fetch data dari PostgreSQL, tutup koneksi sebelum return."""
        conn = None
        try:
            cfg = self.sync_config_id
            _logger.debug('[KA-QC] Koneksi ke %s@%s:%s/%s',
                          cfg.db_user, cfg.db_host, cfg.db_port, cfg.db_name)
            conn = psycopg2.connect(
                host=cfg.db_host, port=cfg.db_port,
                dbname=cfg.db_name, user=cfg.db_user,
                password=cfg.db_password, connect_timeout=10,
            )
            cur = conn.cursor()

            base_sql = """
                SELECT
                    no_spta, kd_antrian,
                    pos_brix, varietas_brix,
                    brix_core, pol_core, rend_core,
                    brix_ari,  pol_ari,  rend_ari,
                    rend_npp, rend_perjam, rend_harian,
                    created_at, updated_at
                FROM public.data_analisa_qc
            """

            if date_from and date_to:
                _logger.debug('[KA-QC] Mode MANUAL | %s s/d %s', date_from, date_to)
                cur.execute(base_sql + " WHERE created_at BETWEEN %s AND %s ORDER BY created_at DESC",
                            (date_from, date_to))
            elif cron_mode:
                cron_start = _dt.date(CRON_SYNC_FROM_YEAR, 1, 1)
                cron_end   = _dt.date(CRON_SYNC_FROM_YEAR + 1, 1, 1)
                _logger.debug('[KA-QC] Mode CRON | tahun %d', CRON_SYNC_FROM_YEAR)
                cur.execute(base_sql + " WHERE created_at >= %s AND created_at < %s ORDER BY created_at DESC",
                            (cron_start, cron_end))
            else:
                cur.execute(base_sql + " ORDER BY created_at DESC")

            rows = cur.fetchall()
            _logger.debug('[KA-QC] ✓ Data ditemukan: %d record', len(rows))

            result = []
            for row in rows:
                result.append({
                    'no_spta':       row[0],
                    'kd_antrian':    row[1],
                    'pos_brix':      row[2],
                    'varietas_brix': row[3],
                    'brix_core':     row[4],
                    'pol_core':      row[5],
                    'rend_core':     row[6],
                    'brix_ari':      row[7],
                    'pol_ari':       row[8],
                    'rend_ari':      row[9],
                    'rend_npp':      row[10],
                    'rend_perjam':   row[11],
                    'rend_harian':   row[12],
                    'created_at':    (row[13] - TZ_OFFSET) if row[13] else False,
                    'updated_at':    (row[14] - TZ_OFFSET) if row[14] else False,
                })
            return result

        except Exception as e:
            _logger.error('[KA-QC] ✗ Gagal fetch: %s', str(e))
            raise UserError(_('Gagal fetch dari PostgreSQL: %s') % str(e))
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _do_sync(self, date_from=None, date_to=None, cron_mode=False):
        """
        Core sync:
        1. Fetch dari PostgreSQL (koneksi ditutup)
        2. Upsert ke ka.analisa.qc
        3. Link rend_npp ke ka.timbang.tebu via kd_antrian
        """
        self.ensure_one()
        sync_type  = 'MANUAL' if (date_from and date_to) else 'CRON'
        start_time = _dt.datetime.now()

        rows = self._fetch_from_postgres(
            date_from=date_from, date_to=date_to, cron_mode=cron_mode
        )
        total_rows = len(rows)
        if total_rows == 0:
            _logger.info('[KA-QC] Tidak ada data baru.')
            return 0

        ctx = dict(tracking_disable=True, mail_notrack=True, mail_create_nolog=True)
        company = self.company_id
        company_id = company.id
        Qc     = self.env['ka.analisa.qc'].sudo().with_context(**ctx).with_company(company)
        Timbang = self.env['ka.timbang.tebu'].sudo().with_context(**ctx).with_company(company)

        # Pre-load cache existing QC (no_spta → id) via SQL langsung
        # supaya tidak terpengaruh record rule / company filter
        self.env.cr.execute(
            "SELECT no_spta, id FROM ka_analisa_qc WHERE company_id = %s",
            (company_id,)
        )
        existing_qc = {row[0]: row[1] for row in self.env.cr.fetchall()}
        # Pre-load cache timbang (kd_antrian → id)
        timbang_cache = {
            r['kd_antrian']: r['id']
            for r in Timbang.search_read(
                [('kd_antrian', '!=', False), ('company_id', '=', company_id)],
                ['kd_antrian', 'id']
            )
        }

        vals_create  = []
        vals_update  = []   # list of (id, vals)
        count_insert = 0
        count_update = 0
        count_linked = 0

        for row in rows:
            no_spta    = row['no_spta'] or ''
            kd_antrian = str(row['kd_antrian']) if row['kd_antrian'] else ''

            # Cari link ke timbang
            timbang_id = timbang_cache.get(kd_antrian, False)

            vals = {
                'no_spta':       no_spta,
                'kd_antrian':    kd_antrian,
                'timbang_id':    timbang_id,
                'pos_brix':      float(row['pos_brix'] or 0),
                'varietas_brix': row['varietas_brix'] or '',
                'brix_core':     float(row['brix_core'] or 0),
                'pol_core':      float(row['pol_core'] or 0),
                'rend_core':     float(row['rend_core'] or 0),
                'brix_ari':      float(row['brix_ari'] or 0),
                'pol_ari':       float(row['pol_ari'] or 0),
                'rend_ari':      float(row['rend_ari'] or 0),
                'rend_npp':      float(row['rend_npp'] or 0),
                'rend_perjam':   float(row['rend_perjam'] or 0),
                'rend_harian':   float(row['rend_harian'] or 0),
                'created_at':    row['created_at'],
                'updated_at':    row['updated_at'],
            }

            if no_spta in existing_qc:
                vals_update.append((existing_qc[no_spta], vals))
            else:
                vals_create.append(vals)

        # Batch create dengan proteksi savepoint
        if vals_create:
            try:
                with self.env.cr.savepoint():
                    Qc.create(vals_create)
                count_insert = len(vals_create)
            except Exception as e:
                _logger.warning('[KA-QC] Batch create gagal (%s), fallback per record...', str(e))
                # Fallback: create satu per satu, skip yang duplikat
                for v in vals_create:
                    try:
                        with self.env.cr.savepoint():
                            Qc.create([v])
                        count_insert += 1
                    except Exception:
                        # Sudah ada (race/duplikat) → update saja
                        existing = Qc.search([
                            ('no_spta', '=', v['no_spta']),
                            ('company_id', '=', company_id),
                        ], limit=1)
                        if existing:
                            existing.write(v)
                            count_update += 1

        # Batch update
        BATCH = 500
        for i in range(0, len(vals_update), BATCH):
            batch = vals_update[i:i+BATCH]
            for rec_id, rec_vals in batch:
                Qc.browse(rec_id).write(rec_vals)
            count_update += len(batch)

        # ── Update rend_npp ke field RENDEMEN di ka_timbang_tebu (via kd_antrian) ──
        # PENTING: update kolom 'rendemen', BUKAN 'rafaksi'.
        # rafaksi adalah data asli dari timbangan, tidak boleh ditimpa.
        for row in rows:
            kd_antrian = str(row['kd_antrian']) if row['kd_antrian'] else ''
            rend_npp   = float(row['rend_npp'] or 0)
            if kd_antrian and kd_antrian in timbang_cache:
                timbang_rec = Timbang.browse(timbang_cache[kd_antrian])
                if timbang_rec.rendemen != rend_npp:
                    timbang_rec.write({'rendemen': rend_npp})
                    count_linked += 1

        elapsed = (_dt.datetime.now() - start_time).total_seconds()
        _logger.info(
            '[KA-QC] ✓ Sync %s selesai | Insert: %d | Update: %d | Linked: %d | %.2fs',
            sync_type, count_insert, count_update, count_linked, elapsed
        )
        return count_insert + count_update

    @api.model
    def cron_sync_analisa_qc(self):
        """Cron: sync otomatis data QC tahun berjalan untuk SEMUA company."""
        configs = self.search([('active', '=', True)])
        if not configs:
            _logger.warning('[KA-QC] Tidak ada konfigurasi aktif.')
            return
        for cfg in configs:
            _logger.info('[KA-QC] Sync CRON | Config: %s | Company: %s | Tahun: %d',
                         cfg.name, cfg.company_id.name, CRON_SYNC_FROM_YEAR)
            try:
                count = cfg._do_sync(cron_mode=True)
                cfg.write({
                    'last_sync':         fields.Datetime.now(),
                    'last_sync_status':  'success',
                    'last_sync_message': f'Cron sync: {count} record (company: {cfg.company_id.name}).',
                    'total_synced':      cfg.total_synced + count,
                })
            except Exception as e:
                _logger.error('[KA-QC] ✗ Cron GAGAL | Company: %s | %s', cfg.company_id.name, str(e))
                cfg.write({
                    'last_sync':        fields.Datetime.now(),
                    'last_sync_status': 'failed',
                    'last_sync_message': str(e),
                })
