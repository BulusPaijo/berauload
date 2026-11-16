# Upgrade BerauLoad 1.5.0-stage4.2 → 1.6.0-stage1

**Perubahan skema additive — wajib backup dan cek integritas terlebih dahulu.** Jangan terapkan patch jika `/api/health` tidak menunjukkan `1.5.0-stage4.2`. Jangan gunakan `deploy/install.sh` pada server aktif.

## A. Backup database, uploads, source

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
cd /opt/berauload
tar -czf "BerauLoad_source_before_v160_stage1_$(date +%Y%m%d_%H%M%S).tar.gz" \
  --exclude='node_modules' --exclude='.qa-venv' --exclude='backups' \
  --exclude='.env' BerauLoad_V1_1_1
```

Periksa kedua arsip backup `berauload_db_*.sql.gz`, `berauload_uploads_*.tar.gz`, serta arsip source. **Jaga `.env`**, volume DB `berauload_pgdata` dan volume uploads `berauload_uploads` tetap utuh. Simpan nama dan checksum backup untuk rollback.

## B. Patch ke source aktif dan pengujian

Upload `BerauLoad_V1_6_0_STAGE1_Patch_From_STAGE4_2.zip` ke `/opt/`, lalu:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_6_0_STAGE1_Patch_From_STAGE4_2.zip -d .
./deploy/test.sh
node --test frontend/tests/topology*.test.mjs
docker compose build
```

**Jika salah satu gagal, jangan jalankan `up`.** Catat error build yang pertama. Test lokal bukan pengganti smoke test PostgreSQL.

Hanya setelah build sukses:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Versi yang diharapkan: `1.6.0-stage1`. Semua halaman lama tetap dapat digunakan. Tidak ada pemilih unit atau filter data.

## C. Verifikasi backfill PostgreSQL (read-only)

```bash
cd /opt/berauload/BerauLoad_V1_1_1
set -a; source .env; set +a
# Hanya SELECT, jangan UPDATE data operasional
# Jangan tempel password dari .env ke chat.
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
SELECT id,code,name,level,parent_id,active FROM org_units ORDER BY id;
SELECT 'assets' entity, COUNT(*) total, COUNT(unit_id) linked FROM assets
UNION ALL SELECT 'metrics',COUNT(*),COUNT(unit_id) FROM metrics
UNION ALL SELECT 'import_batches',COUNT(*),COUNT(unit_id) FROM import_batches;
SELECT code, role_key FROM metrics WHERE code IN
  ('beban_sistem_kw','daya_pasok_pembangkit_kw') ORDER BY code;
SELECT (SELECT COUNT(*) FROM users) AS users_legacy,
       (SELECT COUNT(*) FROM user_unit_access a JOIN org_units u
        ON u.id=a.unit_id WHERE u.code='up3_berau') AS up3_access;
SELECT (SELECT COUNT(*) FROM day_states) AS legacy_days,
       (SELECT COUNT(*) FROM unit_day_states u JOIN org_units o
        ON o.id=u.unit_id WHERE o.code='up3_berau') AS mirrored_days;
SELECT version FROM schema_migrations
 WHERE version='20261115_11_org_units_stage1';
SQL
```

Pada upgrade awal sebelum admin menambahkan unit: hanya satu UP3 dan belum ada ULP/KP. Ketiga kolom linked harus sama dengan total. Dua `role_key` terisi, jumlah users dan akses UP3 sama, jumlah day_states dan mirror UP3 sama. **Jangan ubah isi readings, hour_records, atau day_states menggunakan script.** Bandingkan hitungan dan sampel H/J dari dashboard sebelum/sesudah.

## D. Smoke test browser / peran

1. Admin → Pengaturan → Struktur Organisasi: pohon awal UP3 Berau; coba tambah **ULP berdasarkan nama/kode nyata**, lalu KP, ubah nama, uji larangan nonaktif jika ada anak aktif dan uji pembatasan UP3.
2. Admin → Parameter → Ubah: role_key opsional; legacy `beban_sistem_kw` dan `daya_pasok_pembangkit_kw` sudah memiliki mapping semantik. Coba kode invalid dan duplikat tanpa mengubah mapping resmi.
3. Login operator/verifier/management: halaman/izin tetap sama seperti Stage 4.2, tidak ada filter unit. Cek input, H/J, Topologi, Dashboard, Import, Laporan, dan pengguna.
4. Verify/Finalize/Reopen pada **hari uji yang aman** (jangan mengubah laporan resmi tanpa persetujuan); cek `unit_day_states` selalu sama dengan `day_states` untuk UP3.
5. Periksa console browser dan logs backend; kirim hasil untuk pencatatan `QA_STATUS.md`.

## E. Rollback source tanpa menghapus volume

Jika UI/build tidak berjalan, pulihkan **source sebelum patch** dari arsip tar di direktori yang sama, **tanpa menimpa `.env`, `backups` atau volume**. Build lalu jalankan ulang image lama (`docker compose build && docker compose up -d --no-build`) dan smoke test. Skema V1.6.0 additive: tabel/kolom baru boleh dibiarkan; source Stage 4.2 lama mengabaikannya. **Jangan menjalankan `docker compose down -v` dan jangan DROP tabel baru.**

Jika database mengalami masalah, tinjau backup SQL terlebih dahulu; pemulihan database penuh akan menghapus transaksi setelah backup dan tidak boleh dilakukan otomatis. Diskusikan dampak data sejak waktu backup sebelum restore. Setelah rollback code, alur status harian lama tidak dual-write; catat periode tersebut sebelum kembali ke versi baru.

## F. Keterbatasan QA

`QA_STATUS.md`: regresi Python/SQLite dan JS tersedia. Docker/PostgreSQL/browser serta TypeScript build asli masih harus diverifikasi di LXC pengguna.
