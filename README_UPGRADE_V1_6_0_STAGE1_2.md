# Upgrade BerauLoad 1.6.0-stage1.1 → 1.6.0-stage1.2

**Perbaikan startup/migrasi saja; tidak ada perubahan skema database baru.** Gunakan patch Stage 1.1 → 1.2 bila `/api/health` menyatakan `1.6.0-stage1.1`. Untuk basis Stage 4.2 atau Stage 1, terapkan upgrade yang sesuai urutan atau gunakan Full Source hanya setelah prosedur backup/staging diverifikasi. Jangan menggunakan patch dari versi berbeda.

## Backup dan penghentian aktivitas

1. Pastikan sumber aplikasi yang aktif dan lakukan di jendela maintenance saat input/import tidak berjalan. Jangan menyalakan dua versi backend sekaligus.
2. `cd /opt/berauload/BerauLoad_V1_1_1`; cek `curl -fsS http://127.0.0.1:8092/api/health`.
3. Jalankan `./deploy/backup.sh`; pastikan dump PostgreSQL dan arsip uploads benar-benar ada dan dapat dibaca. Simpan `.env` secara aman tanpa membagikan isinya.
4. Backup source lengkap di lokasi di luar folder aplikasi, contohnya `tar --exclude='.qa-venv' --exclude='node_modules' -czf /opt/berauload_source_before_1612.tar.gz .`.
5. Catat keadaan sebelum upgrade (query read-only di bawah), termasuk satu atau lebih parameter computed UP3 dan penugasan user khusus bila ada.

## Pasang patch dan tes

Upload `BerauLoad_V1_6_0_STAGE1_2_Patch_From_STAGE1_1.zip` ke `/opt/`, lalu dari root source:

```bash
unzip -o /opt/BerauLoad_V1_6_0_STAGE1_2_Patch_From_STAGE1_1.zip -d .
./deploy/test.sh
PYTHONPATH=backend python -m pytest -q backend/tests  # tanpa skip
node --test frontend/tests/topology*.test.mjs
# Docker menggunakan npm install dan npm run build yang sebenarnya
# Jangan up bila test atau build gagal
docker compose build
```

Jika build berhasil, aktifkan dan cek runtime:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
# Harus: version = 1.6.0-stage1.2
```

## SQL audit sebelum dan sesudah restart (PostgreSQL, read-only)

Jalankan dengan klien SQL DBA yang telah terhubung secara aman ke database BerauLoad. Simpan hasil perbandingan, bukan kredensial. **Jangan UPDATE tabel secara manual.**

```sql
SELECT version FROM schema_migrations
 WHERE version IN ('20261115_11_org_units_stage1',
                   '20261115_12_legacy_home_ulp_tanjung_redeb') ORDER BY version;
SELECT id, code, level, parent_id, legacy_home FROM org_units ORDER BY id;
SELECT o.code AS unit, m.input_mode, COUNT(*) AS metrics
 FROM metrics m JOIN org_units o ON o.id=m.unit_id
 GROUP BY o.code,m.input_mode ORDER BY o.code,m.input_mode;
SELECT o.code AS unit, u.username, u.role AS global_role, a.role AS access_role
 FROM user_unit_access a JOIN users u ON u.id=a.user_id
 JOIN org_units o ON o.id=a.unit_id
 ORDER BY u.username,o.code;
SELECT 'readings' AS table_name, COUNT(*) AS total FROM readings
 UNION ALL SELECT 'hour_records',COUNT(*) FROM hour_records
 UNION ALL SELECT 'day_states',COUNT(*) FROM day_states
 UNION ALL SELECT 'unit_day_states',COUNT(*) FROM unit_day_states;
SELECT COUNT(*) AS import_batches FROM import_batches;
SELECT COUNT(*) AS assets FROM assets;
```

Uji restart **satu kali** setelah memastikan aplikasi stabil (`docker compose restart backend`), lalu jalankan query lagi. Jumlah/baris org_units, metrics, access, unit_day_states, dan pembacaan **tidak boleh berubah akibat restart**. Parameter computed UP3 dan penugasan non-admin UP3 yang sah tetap di tempatnya, demikian juga peran berbeda antar-unit. Hasil `/api/dashboard` dan `/api/monitoring/capacity-vs-load` pada periode yang sama harus identik, jika tidak ada input berjalan.

## Rollback aman

- **Jangan jalankan** `docker compose down -v` atau hapus volume PostgreSQL/uploads.
- Bila build gagal **sebelum deployment**, restore source backup saja; database belum dimigrasikan oleh versi baru.
- Setelah deployment, rollback source ke **Stage 1.1 tidak disarankan**: kode lamanya memutar ulang pemindahan dan akses pada setiap startup, yang dapat memicu perubahan data atau gagal startup bila peran lintas unit berbeda. Jika terpaksa rollback versi lama, hentikan backend dan rencanakan restore **source + database + uploads** dari backup yang konsisten dalam maintenance terkontrol. Restore database bisa menghilangkan transaksi setelah titik backup; pastikan disetujui administrator.
- Untuk kesalahan API atau UI tanpa perubahan data, pertimbangkan mempertahankan migrasi yang aman dan menyelesaikan perbaikan di atas Stage 1.2, daripada menyalakan kembali migrator Stage 1.1.
- Log troubleshooting: `docker compose logs --tail=120 backend` (redaksi kredensial sebelum dibagikan).

## QA dan keterbatasan

SQLite sintetis dan regresi otomatis tercatat di `QA_STATUS.md`. **Build npm asli, PostgreSQL 16, dan Docker/browser LXC belum divalidasi di lingkungan pengembangan ini.** Kirim hasil `./deploy/test.sh`, `docker compose build`, `docker compose ps`, smoke test, hasil query sebelum/sesudah restart, dan `/api/health` (tanpa kata sandi) agar QA_STATUS bisa diperbarui berdasarkan bukti nyata.
