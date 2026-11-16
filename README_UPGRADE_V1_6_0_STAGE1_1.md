# Upgrade BerauLoad V1.6.0 Stage 1.1 — Legacy Home ULP Tanjung Redeb

**Basis:** V1.6.0 Stage 1 **atau** V1.5.0 Stage 4.2. Pilih ZIP patch sesuai versi yang benar. Jangan menerapkan patch Stage 1 ke Stage 4.2 atau sebaliknya.

## 1. Sebelum upgrade

1. Verifikasi `curl -fsS http://127.0.0.1:8092/api/health` dan lihat versi lama.
2. Jalankan `./deploy/backup.sh` dan **pastikan** arsip SQL dan uploads muncul serta dapat dibaca; backup ini belum menggantikan uji restore.
3. Simpan seluruh source dan `.env` di lokasi luar direktori yang di-overlay, misalnya `tar --exclude='.qa-venv' --exclude='node_modules' -czf /opt/berauload_source_before_1611.tar.gz .` dari root source. Simpan terpisah dari volume PostgreSQL.
4. Lakukan dalam jendela maintenance. Hentikan input/import sementara untuk menghindari penulisan saat migrasi; jangan menjalankan dua versi aplikasi bersamaan.
5. Catat hasil query jumlah pembacaan dan status harian sebelum upgrade untuk perbandingan.

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
# Verifikasi berkas backup sebelum melanjutkan
```

## 2. Instalasi

Upload salah satu ZIP ke `/opt/`: `BerauLoad_V1_6_0_STAGE1_1_Patch_From_STAGE1.zip` untuk Stage 1, **atau** `BerauLoad_V1_6_0_STAGE1_1_Patch_From_STAGE4_2.zip` untuk Stage 4.2.

```bash
# GANTI <nama-patch-yang-sesuai> dengan file ZIP yang di-upload
unzip -o /opt/<nama-patch-yang-sesuai>.zip -d .
./deploy/test.sh
node --test frontend/tests/topology*.test.mjs
docker compose build
```

**Catatan QA:** satu tes lama `test_org_units.py::test_api_hierarchy_csrf_access_and_audit` masih mengharapkan UP3 tanpa ULP; tes ini memang bertentangan dengan aturan baru, sehingga skrip test penuh dapat mengembalikan exit code nonzero. Jangan menganggap ini kegagalan build atau mengubah perilaku aplikasi agar tes lama lulus. Periksa semua tes lain; hasil terbaru direkam di `QA_STATUS.md`. Rilis staging hanya dapat dipasang jika admin menerima perbedaan tes legacy yang terdokumentasi.

Bila Docker build berhasil dan pengujian diterima:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
# expected version: 1.6.0-stage1.1
```

Migrasi dipanggil pada startup backend setelah migrasi Stage 1 dan selesai dalam satu transaksi DB. Kegagalan migrasi menghentikan startup, **jangan** menghapus volume atau mengulangi instalasi buta.

## 3. Audit migrasi read-only (PostgreSQL)

Gunakan klien PostgreSQL yang biasa Anda pakai, di database BerauLoad yang benar. Query berikut tidak memuat kredensial:

```sql
SELECT id, code, name, level, parent_id, legacy_home
FROM org_units ORDER BY id;

SELECT (SELECT COUNT(*) FROM assets WHERE unit_id=(SELECT id FROM org_units WHERE level='up3')) AS assets_up3,
       (SELECT COUNT(*) FROM metrics WHERE unit_id=(SELECT id FROM org_units WHERE level='up3')) AS metrics_up3,
       (SELECT COUNT(*) FROM import_batches WHERE unit_id=(SELECT id FROM org_units WHERE level='up3')) AS batches_up3,
       (SELECT COUNT(*) FROM unit_day_states WHERE unit_id=(SELECT id FROM org_units WHERE level='up3')) AS statuses_up3;

SELECT 'assets' AS jenis, COUNT(*) AS total, COUNT(*) FILTER (WHERE unit_id=(SELECT id FROM org_units WHERE legacy_home=TRUE)) AS milik_ulp FROM assets
UNION ALL SELECT 'metrics', COUNT(*), COUNT(*) FILTER (WHERE unit_id=(SELECT id FROM org_units WHERE legacy_home=TRUE)) FROM metrics
UNION ALL SELECT 'import_batches', COUNT(*), COUNT(*) FILTER (WHERE unit_id=(SELECT id FROM org_units WHERE legacy_home=TRUE)) FROM import_batches
UNION ALL SELECT 'unit_day_states', COUNT(*), COUNT(*) FILTER (WHERE unit_id=(SELECT id FROM org_units WHERE legacy_home=TRUE)) FROM unit_day_states;

SELECT code, role_key, unit_id FROM metrics
WHERE code IN ('beban_sistem_kw','daya_pasok_pembangkit_kw');

SELECT u.username, u.role, o.code AS akses_unit, a.role AS akses_role
FROM user_unit_access a JOIN users u ON u.id=a.user_id
JOIN org_units o ON o.id=a.unit_id ORDER BY u.username;

SELECT COUNT(*) AS readings FROM readings;
SELECT COUNT(*) AS hour_records FROM hour_records;
SELECT COUNT(*) AS day_states FROM day_states;
SELECT version FROM schema_migrations WHERE version='20261115_12_legacy_home_ulp_tanjung_redeb';
```

**Hasil yang diharapkan:** tepat satu UP3, tepat satu `legacy_home=TRUE` (`ulp_tanjung_redeb`), semua jumlah UP3 di query kedua nol, seluruh baris legacy milik ULP, role_key tetap `system.load`/`system.capacity`, user non-admin punya akses ULP dan admin punya akses UP3. Jumlah `readings`, `hour_records`, `day_states` dan grafik Dashboard / Capacity vs Load sama persis dengan sebelum upgrade.

## 4. Pemeriksaan browser

Pastikan menu Pengaturan → Struktur Organisasi menampilkan UP3 Berau → ULP Tanjung Redeb. Dashboard, Daya Mampu H, Beban J, input, laporan, topologi, dan login/otorisasi harus tetap berperilaku sama. Belum ada pemilih unit dan belum ada filtrasi per unit. Jalankan satu uji input/status harian sintetis atau pada tanggal uji yang disepakati; jangan mengubah hari final produksi untuk QA.

## 5. Rollback aman

- Jangan menggunakan `docker compose down -v`, `docker volume rm`, atau menghapus PostgreSQL.
- **Rollback source saja**: hentikan container backend+web, pulihkan arsip source sebelum patch, build image lama, lalu `docker compose up -d --no-build`. Struktur database additive tetap ada; kode versi lama dapat mengabaikan kolom baru, tetapi di Stage 1 beberapa mirror/akses UP3 dapat terbentuk lagi jika menjalankan penulisan, sehingga source rollback ini bersifat sementara dan perlu audit sebelum upgrade ulang.
- **Rollback penuh keadaan database**: pulihkan dump SQL backup pra-upgrade memakai prosedur restore PostgreSQL yang telah diuji operator DBA, tanpa menghapus Docker volume. Restore dari backup dapat menghilangkan perubahan yang dibuat setelah backup; lakukan hanya dengan persetujuan dan maintenance. Pulihkan pula source dan uploads yang sesuai.
- Jika migrasi gagal, periksa logs (`docker compose logs --tail=100 backend`), kembalikan source, dan kirim error lengkap **tanpa kredensial**. Jangan memperbaiki secara manual dengan UPDATE unit_id yang tidak diaudit.

## 6. Batas validasi

Tes SQLite sintetis berhasil; build frontend lokal tidak dapat diverifikasi karena `npm install` gagal `EAI_AGAIN`, sehingga `npm run build` juga gagal akibat dependensi hilang. PostgreSQL production, Docker Compose, dan browser **belum** diuji di lingkungan pengembangan ini. Kirim hasil uji LXC untuk pembaruan `QA_STATUS.md`.
