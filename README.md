# BerauLoad

Aplikasi web monitoring beban kelistrikan PLN UP3 Berau: pengukuran per jam, rekap historis, Formula Engine, Dashboard Builder, topologi, laporan, dan **Pengukuran Gardu Distribusi**.

**Versi saat ini: 1.6.0-stage9d5** (kandidat staging, 18 November 2026). Catatan tiap versi ada di [CHANGELOG.md](CHANGELOG.md) dan hasil uji di [QA_STATUS_STAGE9D5.md](QA_STATUS_STAGE9D5.md). Narasi tahap lama dipindahkan ke [README_RIWAYAT_TAHAP.md](README_RIWAYAT_TAHAP.md).

## Tampilan aplikasi
Semua tangkapan layar memakai **data contoh sintetis**, bukan data pelanggan atau pengukuran PLN yang sebenarnya.

### Masuk dan input
| | |
|---|---|
| ![Halaman masuk](docs/screenshots/01-login.png)<br>**Halaman masuk** | ![Input massal](docs/screenshots/02-input-massal.png)<br>**Input massal** seperti Excel: tiap jurusan punya warna samar |
| ![Tegangan berwarna](docs/screenshots/03-input-tegangan-berwarna.png)<br>**Tegangan rel F-N, rel F-F, ujung JTR, dan grounding** masing-masing berwarna | ![Master gardu](docs/screenshots/04-master-gardu.png)<br>**Master gardu** per ULP dan KP, bisa impor dari Excel |

### Form ponsel (untuk petugas di lapangan)
| | |
|---|---|
| ![Form ponsel](docs/screenshots/14-form-ponsel-awal.png) | ![Form ponsel, tegangan](docs/screenshots/15-form-ponsel-tegangan.png) |
| Cari nomor gardu, pilih tanggal dan sesi | Kartu per fasa berwarna (R merah, S kuning, T hitam, N biru) |

### Pengukuran dan riwayat
![Daftar pengukuran](docs/screenshots/05-daftar-pengukuran.png)
**Daftar pengukuran** menampilkan kode dan nama gardu, status, dan revisi.

![Rincian, tabel nilai](docs/screenshots/06-rincian-tabel-nilai.png)
**Rincian pengukuran:** tabel mirip Excel. Sel oranye berubah di revisi terakhir, dan nilai lamanya muncul saat kursor diarahkan. Tersedia tombol **Unduh Excel**.

![Rincian, riwayat](docs/screenshots/07-rincian-riwayat.png)
**Riwayat** ditulis dalam bahasa sehari-hari: siapa mengubah apa, dari berapa ke berapa.

### Analisa dan pemantauan
![Analisa](docs/screenshots/08-analisa.png)
**Analisa & Tindak Lanjut:** sebaran kondisi per penyulang, perbandingan sesi, daftar perlu perhatian, dan filter temuan "salah satu / semua".

![Peta](docs/screenshots/09-peta.png)
**Peta gardu** dengan ringkasan overload, tinggi, dan yang belum diukur.

![Tindak lanjut](docs/screenshots/10-tindak-lanjut.png)
**Tindak lanjut:** daftar pekerjaan dari hasil pengukuran, lengkap dengan prioritas dan status.

![Pemantauan](docs/screenshots/11-pemantauan.png)
**Pemantauan & laporan:** cakupan pengukuran per unit dan daftar gardu yang perlu diukur.

![Export](docs/screenshots/12-export.png)
**Export data** ke Excel atau CSV dengan filter dan pilihan kolom.

### Rumus dan kategori
![Rumus dan kategori](docs/screenshots/13-rumus-kategori.png)
**Rumus & Kategori:** kolom hitung dan kategori pembebanan yang bisa diatur admin, termasuk urutan seret-dan-lepas.

### Pemantauan beban harian
![Dashboard](docs/screenshots/20-dashboard.png)
**Dashboard Beban Sistem:** daya mampu dan beban sistem per periode.

![Dashboard Builder](docs/screenshots/21-dashboard-builder.png)
**Dashboard Builder:** susun dashboard sendiri tanpa menulis kode.

![Topologi](docs/screenshots/22-topologi.png)
**Topologi Single Line:** diagram pembangkit, rel, dan penyulang dengan kotak data yang tertaut ke parameter.

![Kelengkapan](docs/screenshots/23-kelengkapan.png)
**Kelengkapan Pengisian Unit:** matriks jam per hari untuk melihat data yang belum terisi.

### Input dan data historis
![Input beban harian](docs/screenshots/24-input-beban.png)
**Input Beban Harian:** formulir per jam dengan tab Pembangkit, Frekuensi & Tegangan, Arus Feeder, dan Rekap.

![Data historis](docs/screenshots/25-data-historis.png)
**Data Historis:** kalender pembacaan per bulan, hijau berarti lengkap.

### Analisis, pembangkit, dan feeder
![Analisis beban](docs/screenshots/26-analisis-beban.png)
**Analisis Beban:** puncak, minimum, dan tren untuk parameter pilihan.

![Pembangkit](docs/screenshots/27-pembangkit.png)
**Monitoring Pembangkit:** tren harian per pembangkit.

![Monitoring feeder](docs/screenshots/28-monitoring-feeder.png)
**Monitoring Feeder:** arus per fasa dan penyulang.

### Laporan, ekspor, impor, dan pengaturan
![Laporan](docs/screenshots/29-laporan.png)
**Laporan & Perbandingan:** ekspor Excel/PDF dan perbandingan parameter antar tahun.

![Export](docs/screenshots/30-export.png)
**Export Data Excel / CSV:** pilih kolom, urutan, dan judul kolom.

![Import](docs/screenshots/31-import.png)
**Import Excel:** unduh template, unggah, dan pratinjau sebelum disimpan.

![Pengaturan](docs/screenshots/32-pengaturan.png)
**Pengaturan:** jenis peralatan, parameter, satuan, pengguna, struktur organisasi, dan audit log.

![Panduan](docs/screenshots/33-panduan.png)
**Panduan Pengguna** bawaan aplikasi, bisa dicetak sebagai PDF.

## Teknologi
- Backend: Python 3.12, FastAPI, SQLAlchemy, openpyxl, ReportLab
- Frontend: React 19, TypeScript, Vite, Recharts
- Database: PostgreSQL 16, dijalankan dengan Docker Compose
- Zona waktu bisnis: Asia/Makassar (WITA). Port web bawaan: 8092

## Fitur Pengukuran Gardu (Stage 9)

- **Saran penanganan overload (9e):** tukar trafo atau pindah beban ke gardu terdekat, dengan tinjauan sebelum/sesudah, tindak lanjut, dan penerapan ke master.
- Master gardu per ULP dan KP, input massal seperti Excel, form ponsel, impor/ekspor Excel
- Hasil hitung, kategori beban, dan temuan yang bisa diatur admin
- Analisa, peta, tindak lanjut, pemantauan cakupan, laporan PDF/Excel
- 9d-5: rincian pengukuran (tabel nilai, riwayat bahasa sehari-hari, unduh Excel), tegangan rel F-N/F-F berwarna, urutan kategori seret-dan-lepas, pemilih temuan "salah satu / semua"

## Pasang baru (server kosong)
**Pemula? Ikuti [PANDUAN_INSTALASI.md](PANDUAN_INSTALASI.md)**: langkah lengkap dari menyiapkan server, memasang Docker, login pertama, sampai backup. Ringkasannya:

Butuh Debian/Ubuntu (LXC atau VM) dengan Docker Engine dan plugin `docker compose`.

```bash
git clone https://github.com/BulusPaijo/berauload.git /opt/berauload/BerauLoad_V1_1_1
cd /opt/berauload/BerauLoad_V1_1_1
./deploy/install.sh
```
Skrip membuat `.env` dengan sandi acak (username `admin`, sandi ditampilkan sekali di layar), lalu membangun dan menjalankan semua layanan. Buka `http://IP-SERVER:8092` dan simpan sandi awal dengan aman.

Setelah itu cek: `curl -fsS http://127.0.0.1:8092/api/health` harus memuat `1.6.0-stage9d5`.

## Upgrade server yang sudah berjalan
Jangan memakai `install.sh` untuk server aktif. Bisa naik langsung dari Stage 8, 9a, 9b, 9c, 9d1, 9d2, 9d3, atau 9d4.

1. Letakkan `BerauLoad_V1_6_0_STAGE9D5_Full_Source.zip` dan `upgrade_to_stage9d5.sh` di `/opt`.
2. Jalankan:
   ```bash
   unzip -tq /opt/BerauLoad_V1_6_0_STAGE9D5_Full_Source.zip
   bash /opt/upgrade_to_stage9d5.sh
   curl -fsS http://127.0.0.1:8092/api/health
   ```
Skrip membuat cadangan database, unggahan, dan source di `backups/upgrade_stage9d5_<waktu>/` sebelum mengganti apa pun. Bila build gagal, versi lama tetap berjalan. Langkah uji manual dan rollback ada di [README_UPGRADE_V1_6_0_STAGE9D5.md](README_UPGRADE_V1_6_0_STAGE9D5.md).

> **Jangan pernah menjalankan `docker compose down -v`.** Perintah itu menghapus volume database.

## Tes
```bash
./deploy/test.sh                                   # tes backend (database SQLite uji, bukan produksi)
cd frontend && npm install --no-audit --no-fund && npm run build
```

## Keamanan
- Batasi akses lewat firewall, VPN, atau reverse proxy HTTPS. Jangan buka langsung ke internet.
- Bila diakses lewat HTTPS, ubah `COOKIE_SECURE=true` di `.env`.
- `.env` dan cadangan database tidak boleh masuk ke Git (sudah ada di `.gitignore`).
- Jalankan `deploy/backup.sh` secara terjadwal.

## Dokumentasi
| Berkas | Isi |
|---|---|
| [PANDUAN_INSTALASI.md](PANDUAN_INSTALASI.md) | Pasang dari nol, pengaturan awal, backup, pemecahan masalah |
| [PANDUAN_PENGGUNA.md](PANDUAN_PENGGUNA.md) | Panduan operator, admin, dan manajemen |
| [ARSITEKTUR.md](ARSITEKTUR.md) | Modul, sumber data, keamanan, migrasi |
| [ATURAN_PROYEK.md](ATURAN_PROYEK.md) | Prinsip pemeliharaan kode |
| [CHANGELOG.md](CHANGELOG.md) | Catatan tiap versi |
| `README_UPGRADE_*.md` | Panduan upgrade per tahap |
| `QA_STATUS_*.md` | Hasil uji per tahap |

## Prinsip data
Kosong berarti belum diukur, bukan nol. Migrasi bersifat aditif dan idempotent. Setiap perubahan data dicatat di audit.
