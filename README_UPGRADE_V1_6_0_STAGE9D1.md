# Upgrade BerauLoad V1.6.0 — Stage 9d-1 (Peta, Grafik, UI)

**Status: kandidat staging. Jangan pasang ke produksi sebelum lulus build Docker, PostgreSQL 16, akses unit, dan smoke test browser nyata.** Full source ini kumulatif: dapat dipasang **langsung dari Stage 9c-fix Rev1**, Stage 9c, atau Stage 9b tanpa memasang tahap di antaranya secara manual. Migrasi 9c-fix dan 9d1 dijalankan oleh aplikasi saat startup sesuai urutan migrasi. Data ukur, data historis, rumus/seed 9b, dan volume PostgreSQL tidak diubah oleh UI tahap ini.

## Sebelum upgrade

1. Uji di **staging dengan salinan produksi**; pastikan tersedia ruang untuk salinan `pg_dump`, `uploads`, dan source aplikasi.
2. Lakukan backup ke media di luar LXC juga. Konfirmasi database `db` dan `backend` sudah berjalan, `docker compose config -q` lulus, versi lama tertera pada `VERSION`.
3. Pastikan Docker dapat mengambil paket `leaflet@1.9.4` dan `@types/leaflet@1.9.15` melalui `npm install`; jika gagal, **jangan ganti container lama**.

### Unggah dan jalankan di LXC

Unduh dua file dari chat, lalu upload ke `/opt/` menggunakan WinSCP:

- `BerauLoad_V1_6_0_STAGE9D1_Full_Source.zip`
- `upgrade_to_stage9d1.sh`

```bash
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
unzip -tq /opt/BerauLoad_V1_6_0_STAGE9D1_Full_Source.zip
bash /opt/upgrade_to_stage9d1.sh
```

Opsional, jika lokasi berbeda:

```bash
APP_DIR=/opt/berauload/BerauLoad_V1_1_1 \
ZIP_FILE=/opt/BerauLoad_V1_6_0_STAGE9D1_Full_Source.zip \
bash /opt/upgrade_to_stage9d1.sh
```

Skrip memeriksa versi asal (`1.6.0-stage9b`, `1.6.0-stage9c`, `1.6.0-stage9c-fix`), menguji arsip ZIP, mencadangkan database PostgreSQL dengan `pg_dump -Fc` dan memeriksa dump memakai `pg_restore --list`, menyalin uploads serta source, merekam SHA256, meng-overlay kode tanpa mengubah `.env`/data, lalu melakukan `docker compose build backend web` sebelum `up -d --no-build`. Proses berhenti pada galat; **backup tidak otomatis di-restore** saat kegagalan. Backup tersimpan dalam `backups/upgrade_stage9d1_<timestamp>/`.

**Tidak ada perintah `docker compose down -v`**. Jangan menghapus volume database.

## Pemeriksaan setelah instalasi

```bash
cd /opt/berauload/BerauLoad_V1_1_1
docker compose ps
docker compose logs --tail=150 backend web
curl -fsS http://127.0.0.1:8092/api/health
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 10;"'
```

Harap tampil `app=BerauLoad`, `version=1.6.0-stage9d1`. Sesuaikan port dengan `APP_PORT` bila berbeda. Periksa migrasi `20261117_20_stage9d1_tiles` hanya sekali, tabel `gardu_tile_settings` berisi satu konfigurasi, lalu restart aplikasi sekali lagi untuk menguji idempotensi. Verifikasi jumlah baris pengukuran dan riwayat formula tidak berubah.

## Smoke test manual wajib (staging)

1. Akun **admin global** dapat mengubah URL dan atribusi ubin melalui halaman Peta; operator/verifier hanya membaca. Coba URL `javascript:` dan URL tanpa `{z}/{x}/{y}`: harus HTTP 422. `tiles.enabled=false` mempertahankan titik dan skala.
2. Buka **Analisa → Peta** dengan filter unit/penyulang/kategori/temuan dan kembali lagi: query filter tetap terbawa, jumlah sesuai. Akun KP tidak melihat gardu di luar KP. Gardu tanpa koordinat sah tidak digambar dan dihitung pada daftar perbaikan master.
3. Ganti pewarnaan kategori/umur/kolom hitung; periksa legenda sesuai definisi admin, kategori dengan bentuk berbeda; klik titik untuk panel nilai hitung 9b, riwayat, jurusan dan Google Maps. Uji **Lokasi saya** di HTTPS/localhost dan pada browser yang menolak izin.
4. Coba **Analisa → grafik** (sebar penyulang, sesi, pareto, tren), ekspor CSV/PNG, simpan jenis grafik dalam tampilan. Angka harus sama dengan hasil tersimpan, bukan rumus yang dihitung di browser.
5. Uji Input 9a, Form ponsel, Master, Daftar Pengukuran, Rumus & Kategori termasuk audit, hak akses, nilai kosong ≠ 0, status verified/final, serta tampilan ponsel/scroll tabel.
6. Periksa ubin OSM lewat jaringan kantor dan Cloudflare Tunnel. Uji bila internet dimatikan (ubin boleh gagal; titik, skala, pesan, dan aplikasi tetap berfungsi). Sesuaikan CSP di reverse proxy hanya jika CSP setempat memblokir hostname ubin; jangan izinkan wildcard luas.
7. Ukur respons peta untuk 5.000 gardu pada perangkat lapangan sebelum pemakaian nyata; target kinerja belum dibuktikan di paket ini.

### Konfigurasi ubin

Default: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`; atribusi `© OpenStreetMap contributors`. Akses ubin memerlukan jaringan ke server ubin (atau ubin internal yang diatur admin). Aplikasi **tidak** membundel data ubin; Leaflet dan CSS-nya dibundel npm, tanpa CDN JavaScript. Ketentuan penggunaan penyedia ubin termasuk atribusi harus dipatuhi. Penyedia OSM publik tidak menjamin kapasitas untuk permintaan massal. **Lokasi saya** memerlukan HTTPS/localhost serta izin pengguna; aplikasi tidak mengirim GPS pengguna ke backend.

## Rollback kode tanpa menghapus data

1. Berhentikan sementara aktivitas tulis saat rollback dan tentukan backup yang sesuai, **jangan restore otomatis database** karena akan menghapus masukan sah setelah backup.
2. Dari root proyek:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
BACKUP=/opt/berauload/BerauLoad_V1_1_1/backups/upgrade_stage9d1_<timestamp>
test -s "$BACKUP/source.tar.gz"
tar -xzf "$BACKUP/source.tar.gz" -C /opt/berauload/BerauLoad_V1_1_1
cat VERSION
docker compose build backend web
docker compose up -d --no-build
docker compose ps
```

Karena migrasi aditif, tabel ubin baru boleh tetap ada dan diabaikan source lama. Jangan `DROP` tabel dan jangan hapus volume. Apabila restore `database.dump` benar-benar diperlukan, lakukan terencana dengan DBA setelah memeriksa data transaksi yang lebih baru.

## Batas QA

Pengujian PostgreSQL 16 nyata, browser/pengukuran jaringan kantor/Cloudflare Tunnel, tampilan ponsel fisik, 5.000 titik, dan build Vite dengan dependensi npm yang lengkap **belum diverifikasi di lingkungan penyiapan paket**. Lihat `QA_STATUS_STAGE9D1.md` untuk perintah dan hasil uji yang telah berjalan.
