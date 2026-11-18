# BerauLoad

Aplikasi web monitoring beban kelistrikan PLN UP3 Berau: pengukuran per jam, rekap historis, Formula Engine, Dashboard Builder, topologi, laporan, dan **Pengukuran Gardu Distribusi**.

**Versi saat ini: 1.6.0-stage9d5** (kandidat staging, 18 November 2026). Catatan tiap versi ada di [CHANGELOG.md](CHANGELOG.md) dan hasil uji di [QA_STATUS_STAGE9D5.md](QA_STATUS_STAGE9D5.md). Narasi tahap lama dipindahkan ke [README_RIWAYAT_TAHAP.md](README_RIWAYAT_TAHAP.md).

## Teknologi
- Backend: Python 3.12, FastAPI, SQLAlchemy, openpyxl, ReportLab
- Frontend: React 19, TypeScript, Vite, Recharts
- Database: PostgreSQL 16, dijalankan dengan Docker Compose
- Zona waktu bisnis: Asia/Makassar (WITA). Port web bawaan: 8092

## Fitur Pengukuran Gardu (Stage 9)
- Master gardu per ULP dan KP, input massal seperti Excel, form ponsel, impor/ekspor Excel
- Hasil hitung, kategori beban, dan temuan yang bisa diatur admin
- Analisa, peta, tindak lanjut, pemantauan cakupan, laporan PDF/Excel
- 9d-5: rincian pengukuran (tabel nilai, riwayat bahasa sehari-hari, unduh Excel), tegangan rel F-N/F-F berwarna, urutan kategori seret-dan-lepas, pemilih temuan "salah satu / semua"

## Pasang baru (server kosong)
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
| [PANDUAN_PENGGUNA.md](PANDUAN_PENGGUNA.md) | Panduan operator, admin, dan manajemen |
| [ARSITEKTUR.md](ARSITEKTUR.md) | Modul, sumber data, keamanan, migrasi |
| [ATURAN_PROYEK.md](ATURAN_PROYEK.md) | Prinsip pemeliharaan kode |
| [CHANGELOG.md](CHANGELOG.md) | Catatan tiap versi |
| `README_UPGRADE_*.md` | Panduan upgrade per tahap |
| `QA_STATUS_*.md` | Hasil uji per tahap |

## Prinsip data
Kosong berarti belum diukur, bukan nol. Migrasi bersifat aditif dan idempotent. Setiap perubahan data dicatat di audit.
