# Upgrade BerauLoad V1.6.0 Stage 1.2 → Stage 2 — Template Import

**Syarat:** server sudah menjalankan `1.6.0-stage1.2`. Instal patch pada staging terlebih dahulu; aplikasi sudah dipakai dengan data nyata di LXC. **Jangan terapkan patch ini pada Stage 1.1 / Stage 4.2 secara langsung.** Tidak ada perubahan source importer lama dan tidak ada rewrite pembacaan historis.

## 1. Backup produksi sebelum mengganti kode

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
# Periksa file SQL.gz dan uploads.tar.gz ada, ukurannya masuk akal, tidak kosong.
mkdir -p /opt/berauload_backup
STAMP=$(date +%Y%m%d_%H%M%S)
tar --exclude='./backups' --exclude='./frontend/node_modules' --exclude='./frontend/dist' \
    --exclude='./.qa-venv' -czf "/opt/berauload_backup/source_before_stage2_${STAMP}.tar.gz" .
```

Backup `./deploy/backup.sh` berisi PostgreSQL SQL.gz dan named volume uploads. Simpan salinan `.env` dan backup database/berkas **di luar folder source** yang akan dioverlay. Pastikan snapshot tersedia di lokasi aman. Lakukan saat tidak ada input/import baru.

## 2. Baseline audit read-only (sebelum upgrade)

Jalankan melalui `docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"` setelah mengekspor isi `.env` (`set -a; source .env; set +a`). Simpan output:

```sql
SELECT count(*) AS readings FROM readings;
SELECT count(*) AS hour_records FROM hour_records;
SELECT count(*) AS day_states FROM day_states;
SELECT id,code,name,legacy_home FROM org_units ORDER BY id;
SELECT count(*) AS import_batches FROM import_batches;
SELECT code,unit_id,role_key FROM metrics
 WHERE code IN ('beban_sistem_kw','daya_pasok_pembangkit_kw');
```

## 3. Overlay patch, tes, dan build sebelum restart

Upload `BerauLoad_V1_6_0_STAGE2_Patch_From_STAGE1_2.zip` ke `/opt/`:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_6_0_STAGE2_Patch_From_STAGE1_2.zip -d .
./deploy/test.sh
node --test frontend/tests/topology*.test.mjs
# Direkomendasikan uji frontend dependency asli:
cd frontend && npm install && npm run build && cd ..
docker compose build
```

**Jangan lanjut ke `up` bila build/tes gagal.** `npm install` membutuhkan akses registry. Saat Docker dibangun, gunakan image dependency resmi yang sama seperti sebelumnya. Tidak diperlukan installer ulang atau pembuatan ulang database.

Jika semua lulus:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Health diharapkan menampilkan `1.6.0-stage2`.

## 4. Verifikasi migrasi

```sql
SELECT version,applied_at FROM schema_migrations
 WHERE version='20261115_13_template_import_batch_kind';
SELECT column_name,data_type FROM information_schema.columns
 WHERE table_name='import_batches' AND column_name='kind';
SELECT COALESCE(kind,'NULL') AS jenis,count(*) AS batch
 FROM import_batches GROUP BY COALESCE(kind,'NULL') ORDER BY jenis;
SELECT count(*) FROM import_batches WHERE kind IS NULL;
SELECT count(*) FROM readings;
SELECT count(*) FROM hour_records;
SELECT count(*) FROM day_states;
```

Semua batch lama harus bernilai `legacy_excel`; belum ada `template` sebelum import pertama. **Jumlah dan nilai** readings/hour_records/day_states tetap seperti baseline (kecuali ada aktivitas input terpisah). Query di atas hanya untuk Postgres; SQLite dipakai dalam tes sintetis, bukan prosedur operasi LXC.

## 5. Smoke test import aman

1. Admin buka Import Excel; pastikan dua tab **Template BerauLoad** dan **Laporan lama**.
2. Unduh template tanggal satu hari, pilih tab `Pembangkit`, cek header 1–3, 24 baris jam, dan `_meta` tersembunyi.
3. Unggah **file kosong** → preview sah dengan 0 pembacaan. Jangan commit jika tidak diperlukan; bila commit, hanya batch metadata disimpan tanpa Reading.
4. Uji pada database staging dengan angka sintetis (nol dan satu angka), konfirmasi pembacaan benar, source `template_import`, batch `template`, dan audit.
5. Periksa `/api/imports` lama (preview/commit arsip bulanan) masih bisa dibuka tanpa perubahan UI pada tab lama. Verifikasi Dashboard serta grafik capacity-vs-load tetap identik untuk data yang belum diimport.
6. Uji user non-admin: management tidak dapat mengunduh/mengunggah; operator dan verifier dapat menggunakan fitur. CSRF POST harus wajib.

## 6. Rollback tanpa menghapus volume

Jika build gagal **sebelum** `docker compose up`, restore source dari tar backup; database belum tersentuh migrasi Stage 2. Jika aplikasi sudah terpasang, hentikan aktivitas input/import, simpan ulang backup saat itu, lalu restore source dan rebuild image lama dari salinan source sebelumnya; biarkan PostgreSQL serta uploads volume tetap ada. **Skema baru additive**, sehingga source Stage 1.2 biasanya dapat mengabaikan kolom `kind` ekstra. Jangan jalankan `docker compose down -v` dan jangan `DROP COLUMN`.

Jika terjadi masalah setelah commit data Stage 2, jangan sekadar mengembalikan database ke snapshot lama: itu akan menghapus pembacaan yang ditambahkan sejak backup. Analisis audit/batch, simpan archive dan backup dulu, dan tentukan tindakan restore terencana. Fitur import lama dan sumber data asli tidak dihapus.

**Status rilis:** paket hanya kandidat staging sampai tes build/DB/UI dilakukan di LXC. Kirim hasil `docker compose build`, `docker compose ps`, smoke test, query migrasi di atas, serta screenshot hasil preview (tanpa data sensitif) agar QA_STATUS dapat diperbarui.
