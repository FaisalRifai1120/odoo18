# -*- coding: utf-8 -*-
import base64
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from .ka_cetak_ngp import CETAK_CHUNK_SIZE

_logger = logging.getLogger(__name__)


class KaCetakPrintJob(models.TransientModel):
    _name = 'ka.cetak.print.job'
    _description = 'Job Cetak NGP (dengan progress)'

    line_ids = fields.Many2many('ka.cetak.ngp.line', string='Baris NGP')
    total = fields.Integer(string='Total', default=0)
    done = fields.Integer(string='Selesai', default=0)
    nama_file = fields.Char(string='Nama File', default='NGP')
    chunk_attachment_ids = fields.Many2many(
        'ir.attachment', 'ka_cetak_job_chunk_rel', 'job_id', 'att_id',
        string='PDF Potongan')
    result_attachment_id = fields.Many2one('ir.attachment', string='Hasil PDF')

    @api.model
    def create_job(self, line_ids, nama_file='NGP'):
        """Buat job baru untuk sekumpulan baris NGP. Kembalikan id job."""
        job = self.create({
            'line_ids': [(6, 0, list(line_ids))],
            'total': len(line_ids),
            'done': 0,
            'nama_file': nama_file or 'NGP',
        })
        return job.id

    def render_next(self):
        """Render satu potongan berikutnya (CETAK_CHUNK_SIZE baris) ke PDF,
        simpan sebagai attachment sementara. Dipanggil berulang dari front-end."""
        self.ensure_one()
        Report = self.env['ir.actions.report']
        report_ref = 'ka_cetak.report_ka_cetak_ngp'
        ids = self.line_ids.ids
        start = self.done
        chunk_ids = ids[start:start + CETAK_CHUNK_SIZE]

        if chunk_ids:
            pdf_content, _fmt = Report._render_qweb_pdf(report_ref, res_ids=chunk_ids)
            att = self.env['ir.attachment'].create({
                'name': 'ngp_chunk_%s_%s.pdf' % (self.id, start),
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'mimetype': 'application/pdf',
                'res_model': self._name,
                'res_id': self.id,
            })
            self.chunk_attachment_ids = [(4, att.id)]
            self.done = min(self.done + len(chunk_ids), self.total)

        return {
            'done': self.done,
            'total': self.total,
            'finished': self.done >= self.total,
        }

    def finalize(self):
        """Gabung semua PDF potongan jadi satu, bersihkan yang sementara,
        kembalikan URL unduhan."""
        self.ensure_one()
        from odoo.tools.pdf import merge_pdf

        chunks = self.chunk_attachment_ids.sorted('id')
        parts = [base64.b64decode(att.datas) for att in chunks]
        if not parts:
            raise UserError(_("Tidak ada data untuk digabung."))

        merged = merge_pdf(parts) if len(parts) > 1 else parts[0]
        result = self.env['ir.attachment'].create({
            'name': '%s.pdf' % (self.nama_file or 'NGP'),
            'type': 'binary',
            'datas': base64.b64encode(merged),
            'mimetype': 'application/pdf',
        })
        self.result_attachment_id = result.id
        # buang PDF potongan sementara
        chunks.unlink()

        return {'url': '/web/content/%s?download=true' % result.id}
