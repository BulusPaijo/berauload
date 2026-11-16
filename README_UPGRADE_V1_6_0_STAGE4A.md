# Upgrade BerauLoad V1.6.0 Stage 3 Hotfix → Stage 4a

**Paket ini hanya Stage 4a, bukan 4b/4c.** Prasyarat source server: `1.6.0-stage3` dengan **TS2552 hotfix** sudah terpasang. Gunakan staging terlebih dahulu karena pembatasan per unit kini aktif. Catat semua perubahan dari baseline sebelum deploy. Jangan menginstal patch pada Stage 2 atau Stage 1.x.

## 1. Pemeriksaan & backup sebelum pemasangan

Lakukan pada maintenance window saat tidak ada input/import berjalan. Lokasi kerja yang digunakan selama ini:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
# Cadangkan juga uploads, konfigurasi, dan source termasuk .env; verifikasi arsip benar-benar ada.
tar -czf /opt/berauload_source_before_stage4a.tar.gz \
  --exclude='./frontend/node_modules' --exclude='./frontend/dist' \
  --exclude='./.pytest_cache' .
```

Pastikan `./deploy/backup.sh` benar-benar menyimpan dump PostgreSQL dan uploads; bila tidak, lakukan `pg_dump` terpisah memakai kredensial dari `.env` secara lokal (jangan menyalinnya ke chat). Simpan dump/arsip pada penyimpanan terpisah. Catat hitungan `readings`, `hour_records`, `day_states`, `unit_day_states`, `org_units`, `assets`, `metrics` dan status harian ULP sebelum pemasangan untuk komparasi.

## 2. Instalasi source, pengujian, build

Unggah `BerauLoad_V1_6_0_STAGE4A_Patch_From_STAGE3_Hotfix.zip` ke `/opt/`. Pada folder source:

```bash
unzip -o /opt/BerauLoad_V1_6_0_STAGE4A_Patch_From_STAGE3_Hotfix.zip -d .
PYTHONPATH=backend python -m pytest -q backend/tests
node --experimental-strip-types --test frontend/tests/*.test.mjs
# Jangan lanjut jika salah satu tes gagal.
docker compose build
```

Bila build lulus, jalankan:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Ekspektasi `/api/health`: `status=ok`, `version=1.6.0-stage4a`. Jangan menjalankan `docker compose down -v`, menghapus volume, atau installer database baru.

## 3. Verifikasi status, ownership, dan izin

Tidak ada migrasi tabel/data baru pada Stage 4a. Query berikut **read-only** dilakukan pada PostgreSQL target (gunakan `psql` yang benar menurut Compose):

```sql
SELECT COUNT(*) AS readings_count FROM readings;
SELECT COUNT(*) AS hour_records_count FROM hour_records;
SELECT COUNT(*) AS day_states_count FROM day_states;
SELECT COUNT(*) AS unit_day_states_count FROM unit_day_states;
SELECT level, code, legacy_home FROM org_units ORDER BY level, code;
SELECT unit_id, COUNT(*) FROM metrics GROUP BY unit_id ORDER BY unit_id;
SELECT unit_id, status, COUNT(*) FROM unit_day_states GROUP BY unit_id,status ORDER BY unit_id,status;
```

Jumlah `readings`, `hour_records`, `day_states` tidak boleh berubah akibat startup saja. Periksa status `unit_day_states` legacy_home identik dengan `day_states` setelah tindakan verify/finalize/reopen pada **data uji**. Bandingkan Dashboard H/J dan Capacity-vs-Load ULP Tanjung Redeb dengan snapshot sebelum upgrade.

Untuk uji izin, login sebagai pengguna sintetis per role. `GET /api/org-units` memberi ID. Gunakan header `X-Unit-Id` hanya untuk ID unit yang dapat diakses; operasi perubahan juga memerlukan cookie sesi dan header CSRF sesuai aplikasi. Pastikan KPI/metric ULP lain tidak muncul saat memilih KP; metric kode ULP lain menghasilkan 404. Operator ULP boleh tulis KP; KP tidak dapat tulis ULP. Admin dapat memilih ULP/KP. Perubahan status unit diuji di staging, termasuk bulk rollback jika salah satu KP belum siap. Jangan menjalankan tes destruktif pada data produksi.

## 4. Rollback tanpa menghapus volume

Jika `docker compose build` gagal, **jangan up**: pulihkan source snapshot sebelum patch dan build ulang. Jika aplikasi sudah berjalan pada Stage 4a, hentikan operasi tulis terlebih dahulu. Restore source lengkap sebelumnya, lalu rebuild/up image lama tanpa menghapus volume. Karena Stage 4a tidak menambah atau mengubah skema, database yang belum menerima penulisan multiunit umumnya dapat digunakan dengan source sebelumnya. **Jika data multiunit baru sudah ditulis, downgrade kode dapat menyembunyikan atau salah menafsirkan data; jangan rollback otomatis.** Untuk rollback data, pulihkan dump PostgreSQL dari sebelum upgrade **hanya setelah menyetujui kehilangan transaksi sejak backup**. Simpan backup setelah upgrade untuk forensik bila diperlukan. Jangan mengaktifkan kembali migrator source 1.1 yang bermasalah.

## 5. QA yang masih diperlukan

Kirim (tanpa data rahasia) hasil `docker compose build`, `docker compose ps`, `./deploy/smoke-test.sh`, versi `/api/health`, dan perbandingan count/status legacy home sebelum/sesudah. Saat tes staging lulus, periksa konfigurasi legacy dan keamanan lintas unit sebelum memberikan persetujuan untuk Tahap 4b. Bukti tersebut dapat memperbarui `QA_STATUS.md`.
