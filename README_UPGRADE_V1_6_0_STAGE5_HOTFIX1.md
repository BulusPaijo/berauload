# Upgrade BerauLoad V1.6.0 Stage 5 → Stage 5 Hotfix 1

**Prasyarat:** Instalasi sudah menjalankan `1.6.0-stage5`; uji dahulu di staging dengan backup DB dan uploads yang bisa direstore. File `BerauLoad_V1_6_0_STAGE5_Hotfix1_Full_Source.zip` diunggah ke `/opt/` LXC. Versi target `1.6.0-stage5-hotfix1`. Jangan melakukan `docker compose down -v`, menghapus PostgreSQL/volume, atau menjalankan pytest dengan database produksi.

## Tahapan di LXC (jalankan bertahap, tanpa `set -e` di shell SSH interaktif)

```bash
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
curl -fsS http://127.0.0.1:8092/api/health
# Lanjut HANYA bila keduanya menunjukkan 1.6.0-stage5
./deploy/backup.sh
# Backup source termasuk .env; jauhkan arsip dari folder yang di-rsync
tar -czf "/opt/berauload_before_stage5_hotfix_$(date +%Y%m%d_%H%M%S).tar.gz" \
  --exclude='./backups' --exclude='./frontend/node_modules' \
  --exclude='./frontend/dist' .

mkdir -p /opt/berauload-stage5-hotfix-extract
unzip -o /opt/BerauLoad_V1_6_0_STAGE5_Hotfix1_Full_Source.zip \
  -d /opt/berauload-stage5-hotfix-extract
# Jika rsync belum ada: apt-get update && apt-get install -y rsync
rsync -a --exclude='.env' --exclude='berauload.db' --exclude='backups/' \
  --exclude='uploads/' --exclude='node_modules/' --exclude='dist/' \
  /opt/berauload-stage5-hotfix-extract/BerauLoad_V1_6_0_STAGE5_Hotfix1/ ./
cat VERSION

# Gunakan virtualenv Python untuk host Debian tanpa alias `python`.
# Persiapkan sekali bila belum ada:
# apt-get install -y python3 python3-venv
# python3 -m venv /opt/berauload-stage5-qa-venv
# /opt/berauload-stage5-qa-venv/bin/pip install -r backend/requirements-dev.txt
PYTHONPATH=backend /opt/berauload-stage5-qa-venv/bin/python -m pytest -q backend/tests
node --experimental-strip-types --test frontend/tests/*.test.mjs \
  frontend/src/features/org-units/unitSelection.test.mjs
(cd frontend && npm install && npm run build)
# STOP bila pytest, Node, npm install, atau npm run build gagal

docker compose build
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

## Pemeriksaan setelah deploy (hanya baca)

```bash
# Versi harus 1.6.0-stage5-hotfix1
curl -fsS http://127.0.0.1:8092/api/health
# Schema tetap memakai migrasi Stage 5, tidak ada penanda migrasi Hotfix baru.
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 8;"'
```

Di browser staging, coba impor satu template **KP** pada hari **draft** dengan parameter input yang memiliki formula eksplisit ULP dan UP3. Setelah commit, pastikan nilai KP terisi sekali dan hasil ULP/UP3 jam yang sama muncul. Coba sumber 0 dan operand lain kosong (hasil harus NULL). Coba ULP verified/final: jangan mengubah nilai rekapnya dan lihat penanda perubahan sumber. Coba hari KP terkunci: import dilewati. Periksa import laporan lama dan angka jam lama di ULP Tanjung Redeb; jangan menyiapkan contoh dengan menimpa data produksi.

## Rollback tanpa hapus volume

Jika tes/build gagal **sebelum** `docker compose up`, container lama masih bisa tetap berjalan; pulihkan source dari arsip `berauload_before_stage5_hotfix_*.tar.gz` di direktori aplikasi (jangan hapus `.env`, `pgdata`, backups, uploads). Bila sudah deploy dan perlu rollback, pulihkan source Stage 5 lalu `docker compose build && docker compose up -d --no-build`; **jangan jalankan `docker compose down -v`**. Hotfix ini tidak membuat migrasi baru; jangan menjalankan restore database kecuali ada masalah data yang dibuktikan, dan pikirkan konsekuensi hilangnya pembacaan yang masuk setelah tanggal backup.

**Catatan QA:** npm install gagal EAI_AGAIN di lingkungan pembuatan paket, dan npm run build belum lulus karena dependency tidak tersedia. Pengujian Docker, browser dan PostgreSQL produksi belum dilaksanakan. Verifikasi sendiri secara staging sebelum memasang di produksi.
