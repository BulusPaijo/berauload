# Upgrade BerauLoad V1.6.0 Stage 7 → Stage 7 Hotfix 1

**Lingkup:** alat uji beban (`deploy/loadtest`), tes dan dokumentasi, perbaikan
sintaks `frontend/nginx.conf` serta permission `deploy/smoke-test.sh`. Satu-satunya
perubahan file aplikasi adalah metadata versi di `backend/app/main.py` dan
`frontend/package.json`; tidak ada perubahan aturan bisnis, API, izin,
perhitungan, atau migrasi database.

**Status:** kandidat staging. `npm install`/`npm run build` pada lingkungan QA
masih gagal akibat DNS npm, bukan dapat dinyatakan lulus. Uji browser/Compose
PostgreSQL harus dijalankan pada staging LXC sebelum keputusan produksi.

## Persiapan, backup, dan overlay source

Unggah `BerauLoad_V1_6_0_STAGE7_Hotfix1_Full_Source.zip` ke `/opt/` pada LXC.

```bash
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
curl -fsS http://127.0.0.1:8092/api/health
# Pastikan versi awal 1.6.0-stage7.
./deploy/backup.sh
# Menyimpan source saat ini, termasuk .env, tanpa database/node_modules besar.
tar -czf "/opt/berauload_before_stage7_hotfix1_$(date +%Y%m%d_%H%M%S).tar.gz" \
  --exclude='./backups' --exclude='./frontend/node_modules' \
  --exclude='./frontend/dist' .
mkdir -p /opt/berauload-stage7-hotfix1-extract
unzip -o /opt/BerauLoad_V1_6_0_STAGE7_Hotfix1_Full_Source.zip \
  -d /opt/berauload-stage7-hotfix1-extract
rsync -a \
  --exclude='.env' --exclude='berauload.db' --exclude='backups/' \
  --exclude='uploads/' --exclude='node_modules/' --exclude='dist/' \
  /opt/berauload-stage7-hotfix1-extract/BerauLoad_V1_6_0_STAGE7_Hotfix1/ \
  /opt/berauload/BerauLoad_V1_1_1/
cat VERSION
chmod +x deploy/smoke-test.sh
```

Versi source sekarang seharusnya `1.6.0-stage7-hotfix1`; container tetap versi
lama sampai dilakukan build dan `up`.

## Pengujian sebelum deploy

Gunakan virtualenv pengujian jika host Debian tidak memiliki alias `python`:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
# Ganti path venv bila memakai virtualenv pengujian yang telah dibuat.
PYTHONPATH=backend:. /opt/berauload-qa-venv/bin/python -m pytest -q backend/tests
node --experimental-strip-types --test frontend/tests/*.test.mjs
(cd frontend && npm install && npm run build)
# Uji logika SQLite hanya terhadap database sintetis baru.
PYTHONPATH=backend:. /opt/berauload-qa-venv/bin/python -m deploy.loadtest.runner \
  --confirm-isolated --asgi-sqlite --fixture /tmp/ignored.json \
  --duration 8 --writers 2 --readers 2 --exports 1
```

**Jangan lanjut** bila salah satu tes atau build gagal. Untuk pengujian nyata
PostgreSQL 16, ikuti `deploy/loadtest/README.md` menggunakan Compose/volume
terisolasi dan port 18092/18093 (tidak boleh mengenai 8092).

## Deploy setelah seluruh pemeriksaan staging lulus

```bash
cd /opt/berauload/BerauLoad_V1_1_1
docker compose build
docker compose up -d --no-build
docker compose ps
docker compose exec web nginx -t
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Hasil diharapkan: `status: ok`, `version: 1.6.0-stage7-hotfix1`, backend/db
healthy, web sehat dan `nginx -t` sukses. Perbaikan regex Nginx sudah dites
sintaks di host QA dengan backend alias digantikan localhost; resolusi alias
`backend` di Docker harus diverifikasi lewat command di atas.

## Pemeriksaan database baca-saja

Hotfix ini **tidak membuat migrasi atau data backfill baru**. Pastikan migrasi
Stage 7 sebelumnya tetap tercatat (koneksi dibaca dari environment DB test/stack
masing-masing):

```bash
docker compose exec db sh -c \
'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
"SELECT version FROM schema_migrations WHERE version = '\''20261116_17_stage7_session_safety'\'';"'
```

Tidak ada alasan mengubah tabel baca, entri formula, ataupun data pelanggan.

## Rollback tanpa menghapus volume

Jika verifikasi setelah deploy gagal, jangan gunakan `docker compose down -v`.
Kembalikan source dari arsip `berauload_before_stage7_hotfix1_*.tar.gz` yang
baru Anda buat (termasuk `frontend/nginx.conf` perbaikan manual bila sebelumnya
ada), setelah memastikan nama arsip yang tepat; lanjutkan `docker compose build`
dan `docker compose up -d --no-build`, lalu cek health. Data PostgreSQL dan
volume uploads tetap dipertahankan. Tidak ada migrasi schema untuk dibatalkan.
