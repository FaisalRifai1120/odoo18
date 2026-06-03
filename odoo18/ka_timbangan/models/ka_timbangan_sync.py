# -*- coding: utf-8 -*-
import logging
import psycopg2
from datetime import datetime, date
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Cron hanya sync tahun berjalan (otomatis)
import datetime as _dt
CRON_SYNC_FROM_YEAR = _dt.date.today().year


class KaTimbangSync(models.Model):
    _name = 'ka.timbang.sync'
    _description = 'Sinkronisasi Timbangan'
    _rec_name = 'name'

    name = fields.Char(string='Nama', required=True, default='Sinkronisasi Timbang Tebu')
    active = fields.Boolean(default=True)
    sync_config_id = fields.Many2one(
        'ka.sync.config', string='Konfigurasi Koneksi',
        required=True, ondelete='restrict'
    )

    # ── Filter sync manual ─────────────────────────────────────
    date_from = fields.Date(string='Tanggal Dari')
    date_to = fields.Date(string='Tanggal Sampai')

    # ── Status ─────────────────────────────────────────────────
    last_sync = fields.Datetime(string='Terakhir Sync', readonly=True)
    last_sync_status = fields.Selection([
        ('success', 'Berhasil'),
        ('failed',  'Gagal'),
    ], string='Status Terakhir', readonly=True)
    last_sync_message = fields.Text(string='Pesan Terakhir', readonly=True)
    total_synced = fields.Integer(string='Total Record Ter-sync', readonly=True)

    def action_sync_manual(self):
        """Sync manual dengan filter rentang tanggal date_out."""
        self.ensure_one()
        if not self.date_from or not self.date_to:
            raise UserError(_('Harap isi Tanggal Dari dan Tanggal Sampai.'))
        if self.date_from > self.date_to:
            raise UserError(_('Tanggal Dari tidak boleh lebih besar dari Tanggal Sampai.'))

        _logger.info('[KA-TIMBANG] ════════════════════════════════════════')
        _logger.debug(
            '[KA-TIMBANG] Sync MANUAL dimulai | Range: %s s/d %s',
            self.date_from, self.date_to
        )

        count = self._do_sync(date_from=self.date_from, date_to=self.date_to)
        self.write({
            'last_sync': fields.Datetime.now(),
            'last_sync_status': 'success',
            'last_sync_message': (
                f'Sync manual berhasil: {count} record diproses '
                f'({self.date_from} s/d {self.date_to}).'
            ),
            'total_synced': self.total_synced + count,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Manual Berhasil',
                'message': f'{count} data timbang tebu berhasil disinkronisasi.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_relink_register(self):
        """
        Isi ulang register_id, petani_id, mbs_id untuk semua record
        yang register_id-nya masih kosong atau perlu diperbarui.
        """
        self.ensure_one()
        Tebu = self.env['ka.timbang.tebu'].sudo()
        Register = self.env['ka.sita.register'].sudo()
        Mbs = self.env['ka.mbs'].sudo()

        # Cache
        register_cache = {}
        petani_cache = {}
        mbs_cache = {}

        # Ambil semua record timbang tebu
        all_tebu = Tebu.search([])
        total = len(all_tebu)
        count_linked = 0
        count_mbs = 0

        _logger.info('[KA-TIMBANG] Relink dimulai | Total record: %d', total)

        for idx, rec in enumerate(all_tebu, start=1):
            vals = {}

            # Relink register_id
            kode = rec.register or ''
            if kode:
                if kode not in register_cache:
                    reg = Register.search([('kode_register', '=', kode)], limit=1)
                    register_cache[kode] = reg.id if reg else False
                    petani_cache[kode] = reg.petani_id.id if reg and reg.petani_id else False
                if register_cache[kode] and rec.register_id.id != register_cache[kode]:
                    vals['register_id'] = register_cache[kode]
                    vals['petani_id']   = petani_cache[kode]
                    count_linked += 1

            # Relink mbs_id
            mbs_kode = rec.mbs_kode or 0
            if mbs_kode:
                if mbs_kode not in mbs_cache:
                    mbs = Mbs.search([('kode', '=', mbs_kode)], limit=1)
                    mbs_cache[mbs_kode] = mbs.id if mbs else False
                if mbs_cache[mbs_kode] and rec.mbs_id.id != mbs_cache[mbs_kode]:
                    vals['mbs_id'] = mbs_cache[mbs_kode]
                    count_mbs += 1

            if vals:
                rec.write(vals)

            if idx % 200 == 0 or idx == total:
                _logger.info(
                    '[KA-TIMBANG] Relink progress: %d/%d | Register: %d | MBS: %d',
                    idx, total, count_linked, count_mbs
                )

        _logger.info(
            '[KA-TIMBANG] ✓ Relink selesai | Register linked: %d | MBS linked: %d',
            count_linked, count_mbs
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Relink Selesai',
                'message': f'{count_linked} register & {count_mbs} MBS berhasil di-relink.',
                'type': 'success',
                'sticky': False,
            }
        }

    def _fetch_from_postgres(self, date_from=None, date_to=None, cron_mode=False):
        """
        Ambil data dari PostgreSQL dan tutup koneksi SEBELUM kembali.
        - Manual  : filter date_out BETWEEN date_from AND date_to
        - Cron    : filter date_out tahun berjalan (otomatis)
        Return: list of dicts
        """
        conn = None
        try:
            cfg = self.sync_config_id
            _logger.debug(
                '[KA-TIMBANG] Menghubungkan ke: %s@%s:%s/%s',
                cfg.db_user, cfg.db_host, cfg.db_port, cfg.db_name
            )
            conn = psycopg2.connect(
                host=cfg.db_host,
                port=cfg.db_port,
                dbname=cfg.db_name,
                user=cfg.db_user,
                password=cfg.db_password,
                connect_timeout=10,
            )
            _logger.debug('[KA-TIMBANG] ✓ Koneksi database berhasil')
            cur = conn.cursor()

            select_cols = """
                SELECT spta_id, no_spta, kd_antrian, register,
                       petak, truck_id, date_in, date_out,
                       weight_in, weight_out, weight_net, weight_kw,
                       rafaksi, bobot_tebu, mbs, varietas,
                       jenis_tebu, state
                FROM public.v_spta_timb_odoo
            """

            if date_from and date_to:
                # Sync manual → rentang bebas
                _logger.debug(
                    '[KA-TIMBANG] Mode: MANUAL | date_out: %s s/d %s',
                    date_from, date_to
                )
                cur.execute(
                    select_cols + " WHERE date_out BETWEEN %s AND %s ORDER BY date_out DESC",
                    (date_from, date_to)
                )
            elif cron_mode:
                # Cron → hanya tahun CRON_SYNC_FROM_YEAR ke atas
                cron_start = _dt.date(CRON_SYNC_FROM_YEAR, 1, 1)
                _logger.debug(
                    '[KA-TIMBANG] Mode: CRON | date_out >= %s (tahun %d ke atas)',
                    cron_start, CRON_SYNC_FROM_YEAR
                )
                cur.execute(
                    select_cols + " WHERE date_out >= %s ORDER BY date_out DESC",
                    (cron_start,)
                )
            else:
                _logger.debug('[KA-TIMBANG] Mode: FULL | Semua data')
                cur.execute(select_cols + " ORDER BY date_out DESC")

            rows = cur.fetchall()
            _logger.debug('[KA-TIMBANG] ✓ Data ditemukan: %d record', len(rows))

            # Konversi ke list of dicts agar tidak ada referensi ke cursor
            result = []
            for row in rows:
                result.append({
                    'spta_id':    row[0],
                    'no_spta':    row[1],
                    'kd_antrian': row[2],
                    'register':   row[3],
                    'petak':      row[4],
                    'truck_id':   row[5],
                    'date_in':    row[6],
                    'date_out':   row[7],
                    'weight_in':  row[8],
                    'weight_out': row[9],
                    'weight_net': row[10],
                    'weight_kw':  row[11],
                    'rafaksi':    row[12],
                    'bobot_tebu': row[13],
                    'mbs':        row[14],
                    'varietas':   row[15],
                    'jenis_tebu': row[16],
                    'state':      row[17],
                })
            return result

        except UserError:
            raise
        except Exception as e:
            _logger.error('[KA-TIMBANG] ✗ Gagal fetch dari PostgreSQL: %s', str(e))
            raise UserError(_('Gagal mengambil data dari PostgreSQL: %s') % str(e))
        finally:
            if conn:
                try:
                    conn.close()
                    _logger.debug('[KA-TIMBANG] ✓ Koneksi PostgreSQL ditutup')
                except Exception:
                    pass

    def _do_sync(self, date_from=None, date_to=None, cron_mode=False):
        """
        Core sync logic.
        Koneksi PostgreSQL ditutup SEBELUM operasi ORM dimulai.
        """
        self.ensure_one()
        sync_type = 'MANUAL' if (date_from and date_to) else 'CRON'
        start_time = datetime.now()

        # Step 1: Fetch dari PostgreSQL (koneksi langsung ditutup)
        rows = self._fetch_from_postgres(
            date_from=date_from, date_to=date_to, cron_mode=cron_mode
        )
        total_rows = len(rows)
        if total_rows == 0:
            _logger.info('[KA-TIMBANG] Tidak ada data baru, sync dilewati.')
            return 0


        # Step 2: Proses dengan Odoo ORM — Batch + Bulk optimized
        ctx = dict(
            tracking_disable=True,
            mail_notrack=True,
            mail_create_nolog=True,
        )
        Tebu     = self.env['ka.timbang.tebu'].sudo().with_context(**ctx)
        Register = self.env['ka.sita.register'].sudo()
        Mbs      = self.env['ka.mbs'].sudo()

        # ── Pre-load semua cache sekaligus (1 query per model) ────
        _logger.debug('[KA-TIMBANG] Pre-loading cache...')

        # Cache register: kode -> (id, petani_id)
        register_recs = Register.search_read([], ['kode_register', 'petani_id'])
        register_cache = {
            r['kode_register']: (r['id'], r['petani_id'][0] if r['petani_id'] else False)
            for r in register_recs
        }

        # Cache MBS: kode -> id
        mbs_recs = Mbs.search_read([], ['kode'])
        mbs_cache = {r['kode']: r['id'] for r in mbs_recs}

        # Cache existing sync_keys: sync_key -> id
        existing_recs = self.env['ka.timbang.tebu'].sudo().search_read(
            [], ['sync_key', 'id']
        )
        existing_keys = {r['sync_key']: r['id'] for r in existing_recs}

        _logger.debug(
            '[KA-TIMBANG] Cache loaded | Register: %d | MBS: %d | Existing: %d',
            len(register_cache), len(mbs_cache), len(existing_keys)
        )

        vals_to_create = []
        vals_to_update = []   # list of (id, vals)
        BATCH_SIZE = 500
        count_insert = 0
        count_update = 0

        _logger.debug('[KA-TIMBANG] Memproses %d record...', total_rows)

        for idx, row in enumerate(rows, start=1):
            spta_id  = row['spta_id']
            truck_id = row['truck_id']
            sync_key = f"{spta_id}_{truck_id or ''}"

            # Resolve dari cache (tanpa query)
            kode_register = row['register'] or ''
            reg_data      = register_cache.get(kode_register, (False, False))
            register_id   = reg_data[0]
            petani_id     = reg_data[1]

            mbs_kode = int(row['mbs']) if row['mbs'] else 0
            mbs_id   = mbs_cache.get(mbs_kode, False)

            weight_net = float(row['weight_net'] or 0)
            rafaksi    = float(row['rafaksi'] or 0)
            weight_kw  = weight_net / 100
            bobot_tebu = weight_kw - rafaksi

            vals = {
                'spta_id':        str(spta_id) if spta_id else '',
                'no_spta':        row['no_spta'] or '',
                'kd_antrian':     str(row['kd_antrian']) if row['kd_antrian'] else '',
                'register':       kode_register,
                'register_id':    register_id,
                'petani_id':      petani_id,
                'petak':          row['petak'] or '',
                'truck_id':       truck_id or '',
                'date_in':        row['date_in'],
                'date_out':       row['date_out'],
                'weight_in':      float(row['weight_in'] or 0),
                'weight_out':     float(row['weight_out'] or 0),
                'weight_net':     weight_net,
                'weight_kw':      weight_kw,
                'rafaksi':        rafaksi,
                'bobot_tebu':     bobot_tebu,
                'bobot_tebu_raw': float(row['bobot_tebu'] or 0),
                'mbs_kode':       mbs_kode,
                'mbs_id':         mbs_id,
                'varietas':       row['varietas'] or '',
                'jenis_tebu':     row['jenis_tebu'] or '',
                'state':          row['state'] or '',
                'sync_key':       sync_key,
            }

            if sync_key in existing_keys:
                vals_to_update.append((existing_keys[sync_key], vals))
            else:
                vals_to_create.append(vals)

            # Flush create batch
            if len(vals_to_create) >= BATCH_SIZE:
                Tebu.create(vals_to_create)
                count_insert += len(vals_to_create)
                _logger.debug('[KA-TIMBANG] Batch INSERT: %d records', len(vals_to_create))
                vals_to_create = []

            # Flush update batch
            if len(vals_to_update) >= BATCH_SIZE:
                ids = [r[0] for r in vals_to_update]
                # Bulk write: group by identical vals tidak practical,
                # pakai write per record tapi dalam satu transaksi
                for rec_id, rec_vals in vals_to_update:
                    Tebu.browse(rec_id).write(rec_vals)
                count_update += len(vals_to_update)
                _logger.debug('[KA-TIMBANG] Batch UPDATE: %d records', len(vals_to_update))
                vals_to_update = []

            if idx % 500 == 0 or idx == total_rows:
                _logger.info(
                    '[KA-TIMBANG] Progress [%s]: %d/%d | Insert: %d | Update: %d',
                    sync_type, idx, total_rows,
                    count_insert + len(vals_to_create),
                    count_update + len(vals_to_update)
                )

        # Flush sisa
        if vals_to_create:
            Tebu.create(vals_to_create)
            count_insert += len(vals_to_create)
            _logger.debug('[KA-TIMBANG] Final batch INSERT: %d records', len(vals_to_create))

        if vals_to_update:
            for rec_id, rec_vals in vals_to_update:
                Tebu.browse(rec_id).write(rec_vals)
            count_update += len(vals_to_update)
            _logger.debug('[KA-TIMBANG] Final batch UPDATE: %d records', len(vals_to_update))

        elapsed = (datetime.now() - start_time).total_seconds()
        _logger.info(
            '[KA-TIMBANG] ✓ Sync %s selesai | Total: %d | Insert: %d | Update: %d | Waktu: %.2fs',
            sync_type, total_rows, count_insert, count_update, elapsed
        )
        _logger.info('[KA-TIMBANG] ════════════════════════════════════════')

        return count_insert + count_update

    @api.model
    def cron_sync_tebu(self):
        """Cron: sync otomatis data tahun 2025 ke atas."""
        configs = self.search([('active', '=', True)], limit=1)
        if not configs:
            _logger.warning('[KA-TIMBANG] Tidak ada konfigurasi sync aktif, cron dilewati.')
            return

        _logger.info('[KA-TIMBANG] ════════════════════════════════════════')
        _logger.info(
            '[KA-TIMBANG] Sync CRON dimulai | Config: %s | Tahun: %d',
            configs.name, CRON_SYNC_FROM_YEAR
        )

        try:
            count = configs._do_sync(cron_mode=True)
            configs.write({
                'last_sync': fields.Datetime.now(),
                'last_sync_status': 'success',
                'last_sync_message': (
                    f'Cron sync berhasil: {count} record diproses '
                    f'(tahun {CRON_SYNC_FROM_YEAR}).'
                ),
                'total_synced': configs.total_synced + count,
            })
        except Exception as e:
            _logger.error('[KA-TIMBANG] ✗ Cron sync GAGAL | Error: %s', str(e))
            configs.write({
                'last_sync': fields.Datetime.now(),
                'last_sync_status': 'failed',
                'last_sync_message': str(e),
            })
