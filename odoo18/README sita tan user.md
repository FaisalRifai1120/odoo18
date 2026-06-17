# KA Modules — Dokumentasi Lengkap

> Suite modul kustom Odoo 18 untuk **PG Kebon Agung (PT Kebon Agung)**.
> Author: **PDE KBA** · Lisensi: LGPL-3 · Penamaan folder: `ka_[nama_modul]`.

---

## Ringkasan Modul

| Modul | Nama Teknis | Versi | Deskripsi |
|-------|-------------|-------|-----------|
| KA User Management | `ka_user_management` | 18.0.3.0 | Manajemen user & hak akses berbasis struktur organisasi |
| KA Tanaman | `ka_tanaman` | 18.0.2.0 | Master data: Wilayah, KUD, Petani |
| KA SITA | `ka_sita` | 18.0.2.0 | Sistem Informasi Tebang & Angkut: Register, SPTA, **Closing (Relaksasi, Ketentuan, NTP, Kwitansi)** |
| KA Timbangan | `ka_timbangan` | 18.0.2.0 | Data timbang tebu (sync) + Analisa QC + Laporan |
| KA Monitoring Giling | `ka_monitoring` | 18.0.6.0 | Monitoring giling & SBH/SPT, laporan harian, rekap & dashboard laba/rugi |

### Urutan dependensi (urutan install)
```
ka_user_management  →  ka_tanaman  →  ka_sita  →  ka_timbangan  →  ka_monitoring
```

---

## Arsitektur & Konvensi Umum

Pola yang dipakai konsisten di seluruh modul:

- **Multi-company.** Semua model punya `company_id` + `ir.rule` global per model agar data terpisah antar PG.
- **Penamaan model** `ka.*` (mis. `ka.sita.register`, `ka.ntp`).
- **Grup hak akses berbasis checkbox.** Grup dibuat **tanpa `implied_ids`** (tidak ada pewarisan otomatis) — tiap grup berdiri sendiri dan dicentang manual. Hak detail ditentukan langsung di `ir.model.access.csv`. Grup dikelompokkan per **sub-kategori bagian** di Settings → Users (lihat ka_user_management).
- **Model transaksional** mewarisi `mail.thread` + `mail.activity.mixin` (chatter), punya `_sql_constraints` unik per-company, dan `name_get`/`_rec_name`.
- **Sinkronisasi DB legacy (FoxPro→PostgreSQL).** Memakai `ka.sync.config` via `psycopg2`: ambil data → **tutup koneksi** → operasi ORM batch (≈500) dengan cache pre-load + `sync_key` untuk upsert. Konteks sinkron memakai `tracking_disable=True, mail_notrack=True, mail_create_nolog=True`. Cron memfilter dinamis per tahun berjalan.
- **Versi & upgrade.** Naikkan versi `18.0.x.0` lalu **Upgrade** modul (bukan reinstall) agar perubahan diterapkan.

---

## 1. Modul `ka_user_management`

Manajemen user & hak akses sesuai struktur organisasi PG.

**Dependensi:** `base`, `mail`

### 1.1 Struktur grup (checkbox, dikelompokkan per bagian)

Sejak v18.0.3.0, grup **tidak lagi memakai hirarki `implied_ids`**. Semua grup tampil sebagai **checkbox** dan dikelompokkan menjadi sub-kategori di Settings → Users (urut via `sequence`):

| Sub-kategori (seksi) | Grup di dalamnya |
|----------------------|------------------|
| **KA · Umum** | Administrator KA, Pemimpin Pabrik, KABAG, KASI, KASUBSI, Operator, PPL |
| **KA · Tanaman** | Kasi / Kasubsi / Operator Tanaman |
| **KA · Tebang Angkut** | Kasi / Kasubsi / Operator Tebang Angkut |
| **KA · Teknik** | Kasi / Kasubsi / Operator Teknik |
| **KA · Pabrikasi** | Kasi / Kasubsi / Operator Pabrikasi |
| **KA · TUK** | Kasi / Kasubsi / Operator TUK |
| **KA · Closing** | Akses Menu Closing *(grup `group_ka_closing`)* |
| **KA · Monitoring Giling** | Monitoring Giling — Manajer / Pengguna *(didefinisikan di `ka_monitoring`)* |

> Catatan teknis: kategori `module_category_ka` kini berjudul "KA · Umum". Sub-kategori lain: `module_category_ka_tanaman`, `_ta`, `_teknik`, `_pabrikasi`, `_tuk`, `_closing`, `_monitoring`. Tiap grup `res.groups` cukup diarahkan `category_id`-nya ke kategori yang sesuai. Karena tampil sebagai checkbox, **hak akses tidak saling mewarisi** — centang sesuai kebutuhan.

### 1.2 Daftar XML ID grup utama

| XML ID | Nama Grup |
|--------|-----------|
| `group_ka_admin` | Administrator KA |
| `group_ka_pimpinan` | Pemimpin Pabrik |
| `group_ka_kabag` | KABAG (Kepala Bagian) |
| `group_ka_kasi` | KASI (Kepala Seksi) |
| `group_ka_kasubsi` | KASUBSI (Kepala Sub Seksi) |
| `group_ka_operator` | Operator |
| `group_ka_ppl` | PPL (Penyuluh Pertanian Lapangan) |
| `group_ka_{kasi,kasubsi,operator}_{tanaman,ta,teknik,pabrikasi,tuk}` | 15 grup per-departemen |
| `group_ka_closing` | Akses Menu Closing |

### 1.3 Model `ka.user.profile`

| Field | Tipe | Keterangan |
|-------|------|------------|
| `user_id` | Many2one(`res.users`) | Akun Odoo terkait |
| `name` | Char | Nama lengkap |
| `nip` | Char | NIP |
| `employee_code` | Char | Kode pegawai (unik) |
| `phone` | Char | No. telepon |
| `email` | Char | Email |
| `role` | Selection | ppl / kasubsi / kasi / kabag / operator / admin (+ pimpinan) |
| `role_label` | Char | Label peran |
| `atasan_id` | Many2one(self) | Atasan langsung |
| `active` / `state` | Boolean / Selection | Status aktif |
| `company_id` | Many2one | Perusahaan |

**Perilaku:** grup Odoo tersinkron otomatis saat profil dibuat/diubah (`_sync_odoo_groups`, termasuk pemetaan ke grup per-departemen). PPL wajib punya atasan.

### 1.4 Menu
```
KA User → Manajemen User → Profil User KA
```

---

## 2. Modul `ka_tanaman`

Master data wilayah, KUD, dan petani.

**Dependensi:** `base`, `mail`, `ka_user_management`

### 2.1 Model Wilayah (berjenjang)

`ka.wilayah.provinsi` → `ka.wilayah.kota` → `ka.wilayah.kecamatan` → `ka.wilayah.desa`. Tiap level punya `kode` (unik) + `nama`, relasi ke induk, dan field `related` otomatis ke atas (mis. desa membawa `kota_id` & `provinsi_id`). Tiap level menyimpan One2many + hitungan jumlah anak.

### 2.2 `ka.kud` — KUD

| Field | Tipe |
|-------|------|
| `kode` | Char (unik) |
| `nama` | Char |
| `kota_id` | Many2one(kota) |
| `kota_nama` | Char (bebas) |
| `alamat` | Text |
| `no_telepon` | Char |

### 2.3 `ka.petani` — Petani

| Field | Tipe |
|-------|------|
| `kode_akun` | Char (unik) |
| `nama` | Char |
| `no_ktp` | Char (unik, 16 digit) |
| `nomor_hp` | Char |
| `no_rekening` / `nama_rekening` / `nama_bank` | Char |
| `jumlah_register` | Integer (computed) |
| `ppl_id` | Many2one(`ka.user.profile`, role=ppl) |

### 2.4 Menu
```
KA Tanaman → Master Data
  ├── Wilayah → Provinsi / Kota / Kecamatan / Desa
  ├── KUD
  └── Petani
```

---

## 3. Modul `ka_sita`

Inti operasional: Register, kuota & penerbitan SPTA, dan seluruh proses **Closing** (Relaksasi, Ketentuan, NTP, Nota Gula, Kwitansi).

**Dependensi:** `base`, `mail`, `ka_user_management`, `ka_tanaman`

### 3.1 Master & SPTA

#### `ka.sita.register` — Register
| Field | Tipe | Keterangan |
|-------|------|------------|
| `kode_register` | Char (unik) | Kode register |
| `nama_register` | Char | Nama register |
| `jenis_register` | Selection | TR / TS |
| `metode` | Selection | SBH / SPT |
| `jenis_pembayaran` | Selection | Harian / Periode |
| `kud_id`, `desa_id`, `kecamatan_id` | Many2one | KUD & lokasi (kecamatan auto dari desa) |
| `petani_id`, `account_petani_id` | Many2one(`ka.petani`) | Petani & akun petani |
| `is_transfer` | Boolean | Jika dicentang, kolom rekening tampil |
| `no_rekening`, `nama_bank`, `nama_rekening`, `no_ktp` | Char | Auto dari petani, masih bisa diedit |

#### `ka.mbs` & `ka.jenis.truk`
Master pendukung: `ka.mbs` (kode + label MBS) dan `ka.jenis.truk` (kode + nama jenis truk).

#### `ka.quota.spta` + `ka.quota.spta.line` — Kuota SPTA
Header kuota (jumlah quota / terpakai / sisa, `state`) dengan baris per KUD/kota (`jumlah_spta`, `jumlah_terisi`, `jumlah_sisa`). Rantai persetujuan: register → KUD → wilayah → kuota.

#### `ka.spta` + `ka.spta.nomor` — Penerbitan SPTA
`ka.spta` (header, no_qts, register, petani, KUD, jenis tebang/truk, jumlah, periode tebang, `state`) menghasilkan beberapa `ka.spta.nomor` dengan **nomor format `DDMMNNNN`** (di-generate per batch agar tidak bentrok unik). Memakai `plot_kud_id` (related tersimpan) untuk domain filter yang andal.

#### `ka.sync.config` — Konfigurasi Sinkronisasi
Koneksi ke DB legacy: `db_host`, `db_port`, `db_name`, `db_user`, `db_password`, plus status sync terakhir. Dipakai lintas-modul (mis. `ka_timbangan`) untuk menarik data.

### 3.2 Closing — Relaksasi

**`ka.relaksasi`** (header: `name`, `tgl_berlaku`, `state`) + **`ka.relaksasi.line`** (`posisi_digit`, `nilai_digit`, `nilai_relaksasi`). Relaksasi mengoreksi rafaksi berdasarkan digit tertentu pada kode register.

### 3.3 Closing — Ketentuan

**`ka.ketentuan`** menyimpan parameter perhitungan bagi hasil per periode. Dipilih saat NTP dan menjadi dasar semua perhitungan gula.

| Field | Keterangan |
|-------|------------|
| `name`, `tgl_berlaku`, `state` | Identitas & masa berlaku (draft/active) |
| `harga_gula`, `harga_tetes` | Harga acuan |
| `faktor_gula`, `faktor_tetes`, `faktor_bh_tetes`, `faktor_nira` | Faktor rendemen |
| `bagi_hasil_default` | BH default untuk register di luar daftar |
| `gula_kawalan_default` | Nilai kawalan untuk register yang **ada di daftar kawalan** |
| `persen_lelang`, `persen_natura` | Pembagian Gula BH (default **80 : 20**, jumlah harus 100%) |
| `titipan_tetes` | Nilai titipan tetes untuk Natura3 |
| `line_ids` (`ka.ketentuan.line`) | Daftar **Bagi Hasil per register** (import Excel: register, bagihasil) |
| `kawalan_line_ids` (`ka.ketentuan.kawalan.line`) | Daftar **register penerima kawalan** (import Excel: register) |

**Helper terpusat** (dipanggil NTP): `get_bagi_hasil_for_register`, `get_kawalan_for_register`, `compute_split_gula`, `compute_natura2_tetes`, `compute_natura3_titipan`, `compute_tetes_tani`.

### 3.4 Closing — NTP (Nota Tebu Petani)

**`ka.ntp`** = dokumen closing per periode. Menarik data timbang dari `ka_timbangan`, menghitung hak petani, dan menghasilkan **Nota Gula per register** + cetak **Kwitansi**.

Field header penting: `periode`, `tgl_awal`/`tgl_akhir`, **`ketentuan_id`** (pilih ketentuan; kosong = auto-pilih ketentuan aktif per waktu timbang untuk estimasi), pengelompokan (`jenis_kelompok`: jenis_register / metode / digit), penanda override (`has_import_*`), field upload & file import tersimpan, dan header kwitansi (`kode_periode`, `kwitansi_kota`, `pejabat_jabatan`, `pejabat_nama`).

**Alur:** Draft → (cron timbangan jalan, perhitungan mengikuti ketentuan aktif untuk **estimasi**) → saat closing user meng-**import** nilai final → **Reproses** → **Selesaikan** (state `done`).

**Override per register (prioritas tertinggi menang):**
```
Import di NTP  >  Ketentuan terpilih/aktif  >  default/0
```
Tersedia 3 import override: Relaksasi (register, %), Bagi Hasil (register, bagihasil), Kawalan (register, kawalan).

**Sub-model NTP:**
- `ka.ntp.line` — detail per truk (indikatif). Menyimpan tebu final, BH, dan komponen gula per truk.
- `ka.ntp.import.relaksasi` / `.bagihasil` / `.kawalan` — staging hasil import override.
- `ka.ntp.nota.gula` — **agregat per register** (sumber data kwitansi).

### 3.5 Rumus Gula — 5 Hak Petani  ⭐

Perhitungan dilakukan **di level register** (jumlahkan Tebu Final dulu, baru hitung gula sekali) agar cocok dengan FoxPro. `floor0` = pembulatan ke bawah; `round` = pembulatan setengah ke atas; `floor2` = ke bawah 2 desimal.

```
Tebu Final (per truk) = netto_relaksasi   (sudah dikoreksi rafaksi & relaksasi)

Per REGISTER:
  Gula BH        = floor0( Σ Tebu Final × bagi_hasil )

  ── Pembagian Gula BH ──
  Natura Kecil   = round( Gula BH × %natura )          ← mis. 20%
  Gula Jual      = Gula BH − Natura Kecil               (lelang/SP gula besar)

  ── Natura tambahan ──
  Natura1 (Kawalan)      = round( Tebu × nilai_kawalan )
  Natura2 (Tetes)        = round( (harga_tetes ÷ harga_gula) × Tebu )
  Natura3 (Sharing Tetes)= round( titipan_tetes × Tebu )

  Gula Total   = Gula Jual + Natura Kecil + Natura1 + Natura2 + Natura3
  Rupiah Total = floor2( Gula Total × harga_gula )
```

**Lima hak petani** yang dijumlahkan menjadi Gula Total: **Gula Jual (lelang)**, **Natura Kecil**, **Natura1 (Kawalan)**, **Natura2 (Tetes)**, **Natura3 (Sharing)**.

> Catatan presisi: simpan `bagi_hasil` dengan **4 desimal** agar `Gula BH` akurat. Selisih ke FoxPro tinggal efek pembulatan tepi (maks ±4 gula per register) bila BH hanya 2 desimal.

### 3.6 Cetakan Kwitansi (QWeb PDF)

Report `ka_sita.report_ka_kwitansi` — **Kwitansi Pembelian Tebu & Penjualan Gula**, satu halaman per register.

- **Cetak per register / terpilih:** tombol **Cetak** di tiap baris Nota Gula + **Cetak Terpilih** (report `report_ka_kwitansi_ng`, model `ka.ntp.nota.gula`).
- **Cetak semua:** tombol **Cetak Semua Kwitansi** (di header list Nota Gula & form NTP).
- **Bagian I — Penjualan Gula** (sudah jadi): Tebu Tergiling, Gula Per Ku Tebu (4 kolom **KW tebu/kualitas** — saat ini bagi hasil di kolom ke-2, sisanya 0; disiapkan untuk PG Trangkil), Jumlah Gula, SP gula besar, SP gula kecil, SP gula kecil 2.
- **Bagian II — Hutang/Piutang** (placeholder, *menyusul via import*): premi, karung, operasional KUD/APTRI, tebang/angkut, koordinasi, bibit, traktor, pinjaman, KUR, BWU, PPH 22.
- Header memakai logo perusahaan + **barcode** nomor register (perlu lib server `rlPyCairo`).

> Prasyarat server cetak PDF: **wkhtmltopdf 0.12.6 (patched Qt)** + **rlPyCairo** (untuk barcode).

### 3.7 Menu
```
KA SITA
  ├── Register
  ├── SPTA → Quota / Per Register / List SPTA
  ├── Master Data → MBS / Jenis Truk
  ├── Sinkronisasi → Konfigurasi Sinkronisasi
  └── Closing → Relaksasi / Ketentuan / NTP (Nota Tebu Petani)
```

---

## 4. Modul `ka_timbangan`

Menarik data timbang tebu dari sistem timbangan (DB legacy) + Analisa QC + laporan.

**Dependensi:** `base`, `mail`, `ka_user_management`, `ka_tanaman`, `ka_sita`

### 4.1 Model
- **`ka.timbang.tebu`** — data timbang per SPTA (bruto, bobot, rafaksi, rendemen, waktu masuk/keluar, register, dll). Diklasifikasikan via `jenis_register` & `metode`. Sumber utama perhitungan tebu di NTP & monitoring.
- **`ka.timbang.sync`** — proses sinkronisasi data timbang (jendela hari giling, batch, upsert via `sync_key`).
- **`ka.analisa.qc`** + **`ka.analisa.qc.sync`** — hasil analisa QC (rendemen/kualitas) per SPTA + sinkronisasinya.
- **Laporan:** `ka.laporan.harian` (header per tanggal) → `ka.laporan.register` / `ka.laporan.ppl` / `ka.laporan.detail` (rekap per register, per PPL, dan detail timbang).

### 4.2 Menu
```
KA Timbangan
  ├── Tebu
  ├── Laporan → Laporan Harian / Rekap per Register / Rekap per PPL / Detail Timbang
  ├── Analisa QC
  └── Sinkronisasi → Sinkronisasi Analisa QC / Konfigurasi Sinkronisasi
```

---

## 5. Modul `ka_monitoring` (Monitoring Giling)

> **Status: pengembangan aktif.** Struktur di bawah sesuai fase pembangunan; detail field dapat berubah.

Monitoring giling 2026: laporan harian, SBH/SPT, rekap & dashboard laba/rugi.

**Dependensi:** `base`, `mail`, `ka_user_management`, `ka_tanaman`, `ka_sita`, `ka_timbangan`

### 5.1 Model (per fase)
| Fase | Model | Fungsi |
|------|-------|--------|
| 1 | `ka.giling.season` | Musim Giling |
| 2 | `ka.giling.periode` | Periode Tutupan |
| 2 | `ka.giling.harga.biaya` | Harga & Biaya |
| 2 | `ka.giling.parameter` | Parameter |
| 3 | `ka.giling.harian` | Laporan Harian Giling (tebu otomatis dari `ka_timbangan`, jendela hari giling 06:00–06:00 WIB) |
| 4 | `ka.giling.analisa` | Analisa Lab |
| 4 | `ka.giling.monitoring.*` | 3 SQL view read-only: **SBH**, **SPT**, **Rekap** |
| 5 | `ka.giling.truk` | Rincian Truk (laba per truk) |

### 5.2 Grup hak akses
`Monitoring Giling — Pengguna` (lihat & input) dan `Monitoring Giling — Manajer` (akses penuh: konfigurasi, ubah, hapus) — tampil di seksi **KA · Monitoring Giling**.

### 5.3 Menu
```
Monitoring Giling
  ├── Input Harian → Laporan Harian Giling / Analisa Lab
  ├── Monitoring → Rekap & Dashboard / Monitoring SBH / Monitoring SPT / Rincian Truk
  └── Konfigurasi → Musim Giling / Periode Tutupan / Harga & Biaya / Parameter
```

---

## Cara Instalasi

1. Salin kelima folder modul ke direktori `addons` Odoo:
   ```
   addons/
   ├── ka_user_management/
   ├── ka_tanaman/
   ├── ka_sita/
   ├── ka_timbangan/
   └── ka_monitoring/
   ```
2. Aktifkan **Developer Mode**.
3. **Apps → Update App List**.
4. Install sesuai urutan dependensi:
   `KA User Management` → `KA Tanaman` → `KA SITA` → `KA Timbangan` → `KA Monitoring Giling`.
5. **Prasyarat server untuk cetak PDF:** pasang **wkhtmltopdf 0.12.6 (patched Qt)** dan **rlPyCairo** (barcode), lalu restart Odoo.

> Saat ada perubahan: naikkan versi modul (`18.0.x.0`) lalu **Upgrade** (bukan reinstall). Bila perubahan menyentuh kategori grup (di `ka_user_management`), upgrade `ka_user_management` lebih dulu sebelum modul yang merujuknya.

---

## Urutan Input Data

```
1. KA User Management → Profil User (PPL, KASUBSI, KASI, KABAG, Operator, Admin)
2. KA Tanaman → Wilayah (Provinsi→Kota→Kecamatan→Desa) → KUD → Petani
3. KA SITA → Register (pilih KUD, Desa, Petani; rekening auto dari petani)
4. KA SITA → SPTA → Quota → terbitkan SPTA (nomor DDMMNNNN)
5. KA Timbangan → Sinkronisasi → tarik data timbang & Analisa QC
6. KA SITA → Closing:
     a. Relaksasi (jika ada koreksi rafaksi)
     b. Ketentuan (harga, faktor, %lelang:natura, BH, kawalan, titipan tetes)
     c. NTP → pilih Ketentuan → (estimasi) → import final → Reproses → Selesaikan
        → Nota Gula per register → Cetak Kwitansi
7. KA Monitoring Giling → Konfigurasi (Musim, Periode, Harga/Biaya, Parameter)
     → Laporan Harian → Monitoring SBH/SPT, Rekap & Dashboard
```

---

## Lampiran — Status Pekerjaan Terkini

| Area | Status |
|------|--------|
| Multi-company, Register, SPTA, Sinkronisasi | ✅ Selesai |
| Closing: Relaksasi, Ketentuan, NTP | ✅ Selesai |
| Rumus 5 hak petani (gula jual, natura kecil, kawalan, tetes, sharing) | ✅ Cocok dengan FoxPro |
| Kwitansi PDF — Bagian I (Penjualan Gula) | ✅ Selesai (per register & cetak semua) |
| Kwitansi PDF — Bagian II (Hutang/Piutang) | ⏳ Placeholder — menyusul via import |
| Cetakan Natura terpisah | ⏳ Direncanakan |
| Penataan grup per bagian (sub-kategori) | ✅ Selesai |
| `ka_monitoring` (laba perusahaan) | 🔧 Pengembangan aktif |

---

*Dokumen ini dihasilkan dari kode aktual modul. Detail `ka_monitoring` bersifat sementara karena modul masih dikembangkan.*
