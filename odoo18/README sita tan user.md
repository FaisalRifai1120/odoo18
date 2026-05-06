# KA Modules — Dokumentasi Lengkap

## Ringkasan Modul

| Modul | Nama Teknis | Deskripsi |
|-------|-------------|-----------|
| ka_user_management | `ka_user_management` | Manajemen User berdasarkan Struktur Organisasi |
| ka_tanaman | `ka_tanaman` | Master Data: Wilayah, KUD, Petani |
| ka_sita | `ka_sita` | Sistem Informasi Tanaman: Register |

---

## 1. Modul `ka_user_management`

### Dependensi
- `base`
- `mail`

### Struktur Organisasi
```
Administrator
    └── KABAG (Kepala Bagian)
            └── KASI (Kepala Seksi)
                    └── KASUBSI (Kepala Sub Seksi)
                                └── PPL (Penyuluh Pertanian Lapangan)
Operator  (berdiri sendiri, setara input data)
```

### Grup Odoo yang Dibuat
| XML ID | Nama Grup | Hak Akses |
|--------|-----------|-----------|
| `group_ka_admin` | Administrator KA | Penuh (CRUD + semua grup) |
| `group_ka_operator` | Operator | Read + Write + Create |
| `group_ka_kabag` | KABAG | Mewarisi KASI |
| `group_ka_kasi` | KASI | Mewarisi KASUBSI |
| `group_ka_kasubsi` | KASUBSI | Mewarisi PPL |
| `group_ka_ppl` | PPL | Read only |

### Model
**`ka.user.profile`**
| Field | Tipe | Keterangan |
|-------|------|------------|
| `user_id` | Many2one(`res.users`) | Akun Odoo terkait |
| `name` | Char | Nama lengkap |
| `nip` | Char | NIP |
| `employee_code` | Char | Kode Pegawai (unique) |
| `phone` | Char | No. Telepon |
| `email` | Char | Email (related dari `user_id`) |
| `role` | Selection | ppl/kasubsi/kasi/kabag/operator/admin |
| `atasan_id` | Many2one(`ka.user.profile`) | Atasan langsung |
| `state` | Selection | active/inactive |

### Catatan Instalasi
Setelah install, grup Odoo akan **otomatis tersinkron** saat membuat atau mengubah profil user. 
PPL **wajib** memiliki atasan.

---

## 2. Modul `ka_tanaman`

### Dependensi
- `base`, `mail`
- `ka_user_management`

### Model

#### `ka.wilayah.provinsi` — Provinsi
| Field | Tipe |
|-------|------|
| `kode` | Char (unique) |
| `nama` | Char |

#### `ka.wilayah.kota` — Kota/Kabupaten
| Field | Tipe |
|-------|------|
| `kode` | Char (unique) |
| `nama` | Char |
| `provinsi_id` | Many2one(provinsi) |

#### `ka.wilayah.kecamatan` — Kecamatan
| Field | Tipe |
|-------|------|
| `kode` | Char (unique) |
| `nama` | Char |
| `kota_id` | Many2one(kota) |
| `provinsi_id` | Related (otomatis) |

#### `ka.wilayah.desa` — Desa/Kelurahan
| Field | Tipe |
|-------|------|
| `kode` | Char (unique) |
| `nama` | Char |
| `kecamatan_id` | Many2one(kecamatan) |
| `kota_id` | Related (otomatis) |
| `provinsi_id` | Related (otomatis) |

#### `ka.kud` — KUD
| Field | Tipe |
|-------|------|
| `kode` | Char (unique) |
| `nama` | Char |
| `kota_id` | Many2one(kota) |
| `kota_nama` | Char (nama bebas) |
| `alamat` | Text |
| `no_telepon` | Char |

#### `ka.petani` — Petani
| Field | Tipe |
|-------|------|
| `kode_akun` | Char (unique) |
| `nama` | Char |
| `no_ktp` | Char (unique, 16 digit) |
| `no_rekening` | Char |
| `nama_rekening` | Char |
| `nama_bank` | Char |
| `nomor_hp` | Char |
| `jumlah_register` | Integer (computed) |
| `ppl_id` | Many2one(ka.user.profile, role=ppl) |

### Menu
```
KA Tanaman
  └── Master Data
        ├── Wilayah
        │     ├── Provinsi
        │     ├── Kota/Kabupaten
        │     ├── Kecamatan
        │     └── Desa/Kelurahan
        ├── KUD
        └── Petani
```

---

## 3. Modul `ka_sita`

### Dependensi
- `base`, `mail`
- `ka_user_management`
- `ka_tanaman`

### Model

#### `ka.sita.register` — Register
| Field | Tipe | Keterangan |
|-------|------|------------|
| `kode_register` | Char (unique) | Kode register |
| `nama_register` | Char | Nama register |
| `jenis_register` | Selection | TR / TS |
| `metode` | Selection | SBH / SPT |
| `jenis_pembayaran` | Selection | Harian / Periode |
| `kud_id` | Many2one(ka.kud) | KUD |
| `desa_id` | Many2one(ka.wilayah.desa) | Desa |
| `kecamatan_id` | Many2one(ka.wilayah.kecamatan) | Kecamatan (auto dari desa) |
| `petani_id` | Many2one(ka.petani) | Petani |
| `account_petani_id` | Many2one(ka.petani) | Account Petani (kode-nama) |
| `is_transfer` | Boolean | Checkbox Transfer |
| `no_rekening` | Char | No. Rekening (auto dari petani, editable) |
| `nama_bank` | Char | Nama Bank (auto dari petani, editable) |
| `nama_rekening` | Char | Nama Rekening (auto dari petani, editable) |
| `no_ktp` | Char | Nomor KTP |

### Perilaku Otomatis (onchange)
- Pilih **Petani** → `no_rekening`, `nama_bank`, `nama_rekening`, `no_ktp` terisi otomatis (masih bisa diedit)
- Pilih **Account Petani** → rekening terisi otomatis
- Pilih **Desa** → `kecamatan_id` terisi otomatis
- Kolom rekening **hanya tampil** jika checkbox **Transfer** dicentang

### Menu
```
KA SITA
  └── Register
```

---

## Cara Instalasi

1. Salin ketiga folder modul ke direktori `addons` Odoo Anda:
   ```
   addons/
   ├── ka_user_management/
   ├── ka_tanaman/
   └── ka_sita/
   ```

2. Aktifkan **Developer Mode** di Odoo.

3. Buka **Apps → Update App List**.

4. Install modul sesuai urutan dependensi:
   1. `KA User Management`
   2. `KA Tanaman`
   3. `KA SITA`

---

## Urutan Input Data

```
1. KA User Management
   → Buat profil user (PPL, KASUBSI, KASI, KABAG, Operator, Admin)

2. KA Tanaman → Master Data → Wilayah
   → Input Provinsi → Kota/Kab → Kecamatan → Desa

3. KA Tanaman → Master Data → KUD
   → Input data KUD

4. KA Tanaman → Master Data → Petani
   → Input data petani (pilih PPL dari daftar user)

5. KA SITA → Register
   → Buat register, pilih KUD, Desa, Petani
   → Rekening otomatis terisi dari data petani
```
