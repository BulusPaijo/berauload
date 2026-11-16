# Upgrade BerauLoad V1.6.0 Stage 5 Hotfix 1 → Stage 6

**PENTING:** kandidat staging. Wajib uji npm/Vite, PostgreSQL dan browser staging; jangan deploy ke LXC produksi jika tes gagal. Stage 6 tidak memiliki migrasi, tidak mengubah pembacaan/final, dan tidak menulis data melalui endpoint kelengkapan. Tautan diagram hanya metadata JSON dan revisi.

**Prasyarat:** source **dan** `/api/health` telah `1.6.0-stage5-hotfix1` (bukan `stage5`, `stage4c`). Upload `BerauLoad_V1_6_0_STAGE6_Full_Source.zip` ke `/opt`.

```bash
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
curl -fsS http://127.0.0.1:8092/api/health
# Jangan lanjut jika baseline belum Stage 5 Hotfix 1.
./deploy/backup.sh
# Arsipkan source dan .env untuk rollback, di luar direktori aplikasi.
tar -czf "/opt/berauload_before_stage6_$(date +%Y%m%d_%H%M%S).tar.gz" \
  --exclude='./backups' --exclude='./frontend/node_modules' --exclude='./frontend/dist' .
mkdir -p /opt/berauload-stage6-extract
unzip -o /opt/BerauLoad_V1_6_0_STAGE6_Full_Source.zip -d /opt/berauload-stage6-extract
rsync -a --exclude='.env' --exclude='berauload.db' --exclude='backups/' \
  --exclude='uploads/' --exclude='node_modules/' --exclude='dist/' \
  /opt/berauload-stage6-extract/BerauLoad_V1_6_0_STAGE6/ ./
cat VERSION
# Gunakan Python venv uji yang sudah tersedia; jangan gunakan database produksi.
PYTHONPATH=backend /opt/berauload-stage5-qa-venv/bin/python -m pytest -q backend/tests
node --experimental-strip-types --test frontend/tests/*.test.mjs
(cd frontend && npm install && npm run build)
# HENTIKAN jika tes/build belum lulus.
docker compose build
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Jika venv belum ada, buat venv terpisah di staging dengan `python3 -m venv /opt/berauload-stage6-qa-venv`, lalu instal `backend/requirements-dev.txt` dan ganti path pengujian di atas. Karena `rsync` sudah diinstal pada LXC pengguna, tidak perlu mengulang instal. Jangan menjalankan `set -e` pada SSH interaktif jika ingin terminal tetap terbuka saat terjadi error; tetap berhenti **manual** jika suatu perintah gagal. Source files dari arsip Full Source memiliki satu direktori induk `BerauLoad_V1_6_0_STAGE6/`.

## Periksa tanpa mengubah data

- Sebelum dan sesudah upgrade, bandingkan `cat VERSION`, `/api/health`, jumlah `hour_records`, `readings`, `unit_day_states`, dan `schema_migrations` menggunakan `SELECT COUNT(*)` baca-saja. Stage 6 **tidak menambah versi schema_migrations** dan startup kedua tidak boleh menambah/menghapus baris karena tahap ini.
- Pada browser staging: admin memilih UP3 → Monitoring → Kelengkapan Unit, cek struktur ULP/KP dan 14 hari terakhir, 0 dan jam kosong, ekspor XLSX. Pilih sel untuk memastikan tanggal dan unit benar.
- Login pengguna operator ULP, verifier ULP, management UP3, dan KP; pastikan KP tidak dapat melihat data induk/ULP lain; management hanya lihat.
- Admin buat dua diagram pada ULP/KP, tautkan simbol ULP ke diagram KP, navigasikan pada tanggal/jam tertentu dan kembali. Uji penolakan arah tautan ke atas/sederajat dan restore tautan ke target terarsip.
- Pastikan jumlah pembacaan, hasil formula dan data final ULP Tanjung Redeb sama. Tidak ada migrasi data pada Stage 6.

## Rollback

**Jangan** gunakan `docker compose down -v` atau hapus volume PostgreSQL. Bila tes sebelum deploy gagal, cukup kembalikan source dari arsip source backup; container lama masih berjalan. Bila sudah deploy, hentikan pembaruan, pulihkan source Stage 5 Hotfix 1 dari arsip, lalu `docker compose build && docker compose up -d --no-build`; periksa `/api/health`. Database tidak perlu diturunkan skemanya karena Stage 6 tidak membuat migrasi. Bila terjadi perubahan data operasional selama uji, lakukan prosedur pemulihan database resmi dari `deploy/backup.sh` sesuai kebijakan dan waktu backup, jangan overwrite data lebih baru tanpa persetujuan.

### Contoh pemeriksaan read-only migrasi pada PostgreSQL

Simpan hasil query **sebelum** dan **sesudah** upgrade di staging dan bandingkan; Stage 6 tidak menambah baris `schema_migrations` atau menyalin data historis. Gunakan kredensial DB dari container resmi, jangan menulis langsung:

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT (SELECT COUNT(*) FROM schema_migrations) AS migrasi,
       (SELECT COUNT(*) FROM hour_records) AS slot_jam,
       (SELECT COUNT(*) FROM readings) AS pembacaan,
       (SELECT COUNT(*) FROM unit_day_states) AS status_hari,
       (SELECT COUNT(*) FROM topology_diagrams) AS diagram;"'
```

Simpan ulang hasil setelah restart kedua. Tidak ada DDL/migrasi Stage 6; perubahan jumlah pembacaan dari aktivitas operasional pengguna sendiri harus dipisahkan dari pengujian upgrade.
