# Upgrade BerauLoad V1.6.0 Stage 4a → Stage 4b

**Status: kandidat staging.** BerauLoad Stage 4a telah digunakan pengguna pada LXC dengan data nyata; Stage 4b belum diuji pada PostgreSQL16/Docker di server pengguna. Jadwalkan maintenance window dan gunakan staging clone data terlebih dahulu. **Jangan jalankan tes sintetis di database produksi.**

## 1. Snapshot lengkap sebelum update

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health   # harus 1.6.0-stage4a
./deploy/backup.sh                            # pg_dump + uploads; cek output benar-benar ada
# Arsipkan source dan .env terpisah; jangan bagikan .env/credential
mkdir -p /opt/berauload_rollback
cp -a .env /opt/berauload_rollback/.env.pre4b
# backup source tidak termasuk backup yang menyalin file rahasia ke tempat umum
umask 077
tar --exclude='./frontend/node_modules' --exclude='./frontend/dist' \
    --exclude='./.pytest_cache' --exclude='./backups' \
    -czf /opt/berauload_rollback/source_pre4b.tar.gz .
```

Sebelum upgrade, ambil snapshot SQL **read-only** (di `psql` database benar menurut compose) dan simpan di tempat aman:

```sql
SELECT 'readings' AS source, COUNT(*) FROM readings
UNION ALL SELECT 'hour_records', COUNT(*) FROM hour_records
UNION ALL SELECT 'day_states', COUNT(*) FROM day_states
UNION ALL SELECT 'unit_day_states', COUNT(*) FROM unit_day_states
UNION ALL SELECT 'import_batches', COUNT(*) FROM import_batches;
SELECT code,id,legacy_home FROM org_units ORDER BY id;
```

## 2. Patch, tes, build dan layanan

Upload `BerauLoad_V1_6_0_STAGE4B_Patch_From_STAGE4A.zip` ke `/opt/`.

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_6_0_STAGE4B_Patch_From_STAGE4A.zip -d .
PYTHONPATH=backend python -m pytest -q backend/tests
node --experimental-strip-types --test frontend/tests/*.test.mjs
npm --prefix frontend install --no-audit --no-fund
npm --prefix frontend run build
docker compose build
```

**Jika gagal tes atau build, jangan `up`**. Jika berhasil:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health   # version 1.6.0-stage4b
```

Tidak ada DROP, perubahan tipe kolom, atau perubahan constraint lama. Migrasi unit_id konfigurasi dijaga versi `20261115_16_unit_configuration_stage4b` dalam `schema_migrations`; pada startup berikutnya tidak ada backfill ulang. Audit log lama **tidak** dibackfill. Untuk konfigurasi pribadi, pemilik dengan tepat satu penugasan ULP/KP diberi kepemilikan unit tersebut; penugasan hanya UP3 atau ambigu menggunakan legacy_home dan jumlah fallback dicatat sekali pada log migrasi.

## 3. Verifikasi backfill SQL baca-saja

```sql
SELECT version,applied_at FROM schema_migrations
WHERE version='20261115_16_unit_configuration_stage4b';
SELECT code,id FROM org_units WHERE legacy_home=TRUE;
SELECT u.code, 'input_form_tabs' AS tbl, COUNT(*) AS rows FROM input_form_tabs t
JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
UNION ALL SELECT u.code,'input_form_placements',COUNT(*) FROM input_form_placements t JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
UNION ALL SELECT u.code,'dashboard_layouts',COUNT(*) FROM dashboard_layouts t JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
UNION ALL SELECT u.code,'dashboard_chart_settings',COUNT(*) FROM dashboard_chart_settings t JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
UNION ALL SELECT u.code,'topology_diagrams',COUNT(*) FROM topology_diagrams t JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
UNION ALL SELECT u.code,'report_templates',COUNT(*) FROM report_templates t JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
UNION ALL SELECT u.code,'export_templates',COUNT(*) FROM export_templates t JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
UNION ALL SELECT u.code,'standard_report_selections',COUNT(*) FROM standard_report_selections t JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
UNION ALL SELECT u.code,'formula_definitions',COUNT(*) FROM formula_definitions t JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
UNION ALL SELECT u.code,'historical_definitions',COUNT(*) FROM historical_definitions t JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
UNION ALL SELECT u.code,'engineering_rules',COUNT(*) FROM engineering_rules t JOIN org_units u ON t.unit_id=u.id GROUP BY u.code
ORDER BY tbl,code;
SELECT
 (SELECT COUNT(*) FROM input_form_tabs WHERE unit_id IS NULL) AS tabs_null,
 (SELECT COUNT(*) FROM input_form_placements WHERE unit_id IS NULL) AS placement_null,
 (SELECT COUNT(*) FROM input_form_revision WHERE unit_id IS NULL) AS form_revision_null,
 (SELECT COUNT(*) FROM dashboard_layouts WHERE unit_id IS NULL) AS dashboard_null,
 (SELECT COUNT(*) FROM dashboard_chart_settings WHERE unit_id IS NULL) AS chart_null,
 (SELECT COUNT(*) FROM topology_diagrams WHERE unit_id IS NULL) AS topology_null,
 (SELECT COUNT(*) FROM report_templates WHERE unit_id IS NULL) AS report_null,
 (SELECT COUNT(*) FROM export_templates WHERE unit_id IS NULL) AS export_null,
 (SELECT COUNT(*) FROM standard_report_selections WHERE unit_id IS NULL) AS standard_null,
 (SELECT COUNT(*) FROM formula_definitions WHERE unit_id IS NULL) AS formula_null,
 (SELECT COUNT(*) FROM historical_definitions WHERE unit_id IS NULL) AS historical_null,
 (SELECT COUNT(*) FROM engineering_rules WHERE unit_id IS NULL) AS rules_null;
SELECT COUNT(*) AS up3_form_tabs FROM input_form_tabs t
JOIN org_units u ON u.id=t.unit_id WHERE u.level='up3';
SELECT COUNT(*) AS up3_placements FROM input_form_placements p
JOIN org_units u ON u.id=p.unit_id WHERE u.level='up3';
-- Audit lama tidak diubah; kolom audit_logs.unit_id boleh NULL.
```

Semua `*_null` harus nol setelah backfill, sedangkan `up3_form_tabs` dan `up3_placements` juga nol. Cocokkan kembali hitungan pembacaan/status dan nilai Dashboard H/J home dari sebelum upgrade. Restart backend **sekali** dan pastikan hitungan konfigurasi tidak berubah:

```bash
docker compose restart backend
docker compose logs --tail=120 backend
```

## 4. Uji staging hak akses dan Salin Pengaturan

Masuk sebagai admin global; kirim header `X-Unit-Id` ID unit target untuk endpoint konfigurasi. Tanpa header admin default `legacy_home`. Buat ULP sintetis di staging, pastikan tab bawaan 5 dan parameter kosong. Uji scope: object ID ULP lain → 404; akun non-admin dapat GET bila unit boleh dibaca, tetapi dilarang menulis konfigurasi. UP3 tidak dapat membuat tab form; boleh menyimpan dashboard/topologi. Uji API copy preview/commit dengan unit tujuan kosong, verifikasi pemetaan code; pastikan `readings/hour_records/day_states` tidak bertambah. Jangan menjalankan copy pada unit produksi yang sudah berisi data.

## 5. Rollback tanpa menghapus volume

**Sebelum menjalankan code Stage 4b:** pulihkan arsip source Stage 4a dan build ulang. **Setelah migrasi, sebelum data konfigurasi multi-unit baru dibuat:** kolom nullable baru biasanya aman bagi source 4a, tetapi lakukan uji staging; source 4a tidak memahami konfigurasi baru. **Jika sudah menyimpan konfigurasi ULP/KP atau melakukan copy:** jangan downgrade kode tanpa analisis sebab source 4a dapat menampilkan/menyimpan konfigurasi salah; utamakan memperbaiki source 4b. Pilihan restore database adalah mengembalikan dump sebelum upgrade pada sistem yang dihentikan menulis, setelah menyetujui bahwa transaksi pascabackup akan hilang. Restore source dan uploads juga dari snapshot konsisten. **Jangan `docker compose down -v`**, menghapus volume, DROP tabel, atau memasang kembali migrator Stage 1.1 lama.

## 6. Bukti QA LXC yang diminta

Kirim tanpa rahasia: log `docker compose build`, `docker compose ps`, smoke test, hasil query count/NULL/unit di atas, serta tangkapan layar operasi Topologi, Form Input, Report Builder ULP Tanjung Redeb. Jika semua lulus, baru lanjut ke **Tahap 4c**.
