# Upgrade BerauLoad V1.6.0 Stage 2 → Stage 3 — Parameter Utama per Unit

**Syarat:** server berjalan `1.6.0-stage2`; upgrade pertama pada staging yang memakai salinan database jika memungkinkan. BerauLoad telah dipakai di LXC pengguna dengan data asli, tetapi versi Stage 3 **belum diverifikasi di LXC tersebut**. Jangan overlay patch Stage 3 ke Stage 1.2 atau Stage 4.2. Tidak ada migrasi skema/data baru pada Stage 3 dan tidak ada pemilih unit.

## 1. Backup database, uploads, source, dan status sebelum upgrade

Lakukan saat tidak ada pengguna menginput/mengimpor/verifikasi. Perintah ini disesuaikan dengan direktori kerja yang pernah dilaporkan; ganti bila berbeda:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
# Verifikasi isi file SQL.gz dan uploads.tar.gz di backups/ tidak kosong.
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /opt/berauload_backup
tar --exclude='./backups' --exclude='./frontend/node_modules' --exclude='./frontend/dist' \
    --exclude='./.qa-venv' -czf "/opt/berauload_backup/source_before_stage3_${STAMP}.tar.gz" .
cp -p .env "/opt/berauload_backup/env_before_stage3_${STAMP}"
```

`.env` memuat rahasia: simpan backup tersebut dengan hak akses terbatas (`chmod 600`), jangan unggah ke chat. Simpan salinan database/volume upload terpisah sebelum memulai perubahan. Jangan jalankan `docker compose down -v`, `DROP TABLE`, atau installer ulang.

**Baseline database read-only:** ekspor variabel dari `.env` pada shell yang dipercaya, lalu jalankan `docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"`. Simpan output query berikut sebelum dan sesudah upgrade:

```sql
SELECT 'readings' AS tabel, count(*) FROM readings
UNION ALL SELECT 'hour_records', count(*) FROM hour_records
UNION ALL SELECT 'day_states', count(*) FROM day_states;
SELECT ou.code AS unit, m.code, m.role_key, m.active
FROM metrics m JOIN org_units ou ON ou.id=m.unit_id
WHERE ou.legacy_home=true ORDER BY m.code;
SELECT version,applied_at FROM schema_migrations ORDER BY applied_at DESC LIMIT 10;
```

Simpan juga respons `GET /api/dashboard?year=<tahun>&month=<bulan>`, `/api/monitoring/capacity-vs-load?start=<tanggal>&end=<tanggal>`, laporan standar, dan `/api/compare?year_a=<tahun>&year_b=<tahun>` pada periode dengan data. Bandingkan nilai, bukan hanya jumlah baris.

## 2. Overlay patch, tes, dan build

Unggah `BerauLoad_V1_6_0_STAGE3_Patch_From_STAGE2.zip` ke `/opt/`. **Jangan jalankan frontend/backend Stage 3 sampai pengujian dan build berhasil.**

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_6_0_STAGE3_Patch_From_STAGE2.zip -d .
./deploy/test.sh
PYTHONPATH=backend python -m pytest -q backend/tests
node --experimental-strip-types --test frontend/tests/*.test.mjs
cd frontend
npm install --no-audit --no-fund
npm run build
cd ..
docker compose build
```

Jika `npm install` gagal karena jaringan, perbaiki akses repository/mirror atau gunakan cache yang telah disetujui sebelum melanjutkan; **jangan menganggap parse TS setara dengan build Vite**. Verifikasi tes dari output aktual. Bila gagal, hentikan rollout dan pulihkan source dari tar sebelum upgrade.

## 3. Menjalankan dan smoke test

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Harus muncul `"version":"1.6.0-stage3"`. Periksa halaman login, Dashboard, Analytics, Compare, Monitoring Kapasitas-vs-Beban, laporan standar, Dashboard Builder, dan Topologi. Pertahankan angka historis H/J REKAP yang sama dengan Stage 2 untuk ULP Tanjung Redeb. Bandingkan baseline query jumlah dan nilai pembacaan, `day_states` dan penanda migrasi; **Stage 3 tidak menjalankan backfill baru**.

## 4. Verifikasi role dan fungsi baru (tanpa mengubah data operasi)

1. Login admin; `/api/catalog` harus mengandung `roles.system.load` dan `roles.system.capacity`, mula-mula menunjuk kode H/J yang sama seperti sebelum upgrade. Jika tidak, periksa `metrics.role_key` melalui SQL di atas; jangan menebak metrik pengganti.
2. Pengaturan → **Parameter utama unit**: dua dropdown parameter aktif, status Teratur/Belum Diatur, simpan memerlukan CSRF. Admin dapat mengubah peran, tetapi lakukan uji perubahan di **staging sintetis** terlebih dahulu agar hasil monitoring produksi tidak sengaja bergeser.
3. GET `/api/metrics/<id>/usage` menampilkan dependensi; mencoba nonaktif parameter yang sedang dipakai tanpa `confirm_disable` harus ditolak HTTP 409. Uji pada metric sintetis di staging, bukan pada sumber operasional.
4. Uji simulasi role kosong di staging: semua endpoint parameter utama default seharusnya HTTP 200 dengan `configured:false`, nilai null dan penjelasan UI “Parameter utama belum diatur”. Kembalikan role awal sebelum menyelesaikan QA.
5. Role H/J bukan agregasi penjumlahan: pengaturan grafik pasangan tetap memakai jam berpasangan, tidak boleh `stacked_bar` jika dua role seri dipakai bersama. `NULL` tetap hilang dan nilai `0` tetap nol.

## 5. Rollback tanpa menghapus volume

**Jika belum `up`:** pulihkan source tar sebelum upgrade; database belum tersentuh oleh Stage 3. **Jika sudah berjalan:** hentikan dahulu aktivitas input, backup lagi kondisi terkini, lalu pulihkan source Stage 2 dari source tar (termasuk perubahan konfigurasi yang relevan) dan bangun ulang image Stage 2. PostgreSQL dan volume uploads tetap terpasang; tidak perlu `docker compose down -v` atau migrasi balik. Bila admin sudah memindahkan `role_key` setelah upgrade, source Stage 2 mungkin mengabaikan role baru tetapi backend lama mengandalkan kode baku H/J; **pulihkan mapping role berdasarkan snapshot terverifikasi** sebelum menggunakan pengaturan lama dan pastikan angka sama. Jangan mengubah `readings` atau `day_states` saat rollback source.

```bash
# Setelah source Stage 2 kembali dan kondisi terverifikasi:
docker compose build
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

**Status rilis: KANDIDAT STAGING.** Build npm asli gagal di lingkungan pengembangan karena DNS EAI_AGAIN, sehingga build Docker/PostgreSQL 16/browser **harus** dikonfirmasi di LXC. Kirim output build, hasil `docker compose ps`, smoke test, respons catalog roles dan perbandingan angka H/J (tanpa kredensial) untuk memperbarui `QA_STATUS.md`.
