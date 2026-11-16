# Upgrade BerauLoad 1.6.0 Stage 4c → UI Hotfix 1

**Status:** Kandidat staging, belum tervalidasi dengan npm build di lingkungan pengembang maupun browser/PostgreSQL 16 produksi. Source ZIP ini berisi full source; pembaruan ini hanya mengubah antarmuka Pengaturan → Pengguna dan metadata versi API.

## Persiapan

- Pastikan aplikasi saat ini memang Stage 4c. Jika masih Stage 4b, lakukan pengujian upgrade Stage 4c lengkap terlebih dahulu sebelum hotfix ini.
- Simpan file `BerauLoad_V1_6_0_STAGE4C_UI_Hotfix1_Full_Source.zip` di `/opt/` pada LXC.
- Jangan hapus volume Docker, `.env`, database, uploads, atau backup.

## Perintah staging (sesuaikan bila path instalasi berbeda)

```bash
set -e
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
# Cadangan source saat ini (di luar direktori aplikasi, termasuk konfigurasi)
tar -czf "/opt/berauload_before_ui_hotfix_$(date +%Y%m%d_%H%M%S).tar.gz" --exclude='./frontend/node_modules' --exclude='./frontend/dist' --exclude='./backups' .
mkdir -p /opt/berauload-ui-hotfix-extract
unzip -o /opt/BerauLoad_V1_6_0_STAGE4C_UI_Hotfix1_Full_Source.zip -d /opt/berauload-ui-hotfix-extract
# Full source berfolder induk; jangan menimpa .env dan data aktif
rsync -a --exclude='.env' --exclude='berauload.db' --exclude='backups/' --exclude='uploads/' --exclude='node_modules/' --exclude='dist/' /opt/berauload-ui-hotfix-extract/BerauLoad_V1_6_0_STAGE4C_UI_Hotfix1/ ./
cat VERSION
PYTHONPATH=backend python -m pytest -q backend/tests
node --experimental-strip-types --test frontend/tests/*.test.mjs frontend/src/features/org-units/unitSelection.test.mjs
(cd frontend && npm install && npm run build)
docker compose build
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

**Berhenti sebelum `docker compose build` / `up` apabila salah satu tes, instalasi npm, atau build gagal.** Jangan gunakan `docker compose down -v`.

## Pemeriksaan

- `/api/health` seharusnya melaporkan `1.6.0-stage4c-ui-hotfix1`.
- Login sebagai admin; Pengaturan → Pengguna menampilkan jenis akun dan checkbox setiap unit. Pilih Operator, centang dua unit berbeda, atur peran berbeda, simpan. Periksa kolom **Akses unit**.
- Pilih Admin dan verifikasi bagian akses unit tersembunyi, serta pesan global tampil.
- Coba buat akun non-admin tanpa unit dan pastikan validasi lokal muncul sebelum permintaan ke server.
- Untuk akun Operator/Verifier/Management, pastikan izin aplikasi tidak berubah. Uji satu akun per peran.
- Tidak ada migrasi pada hotfix ini. Verifikasi read-only `SELECT version FROM schema_migrations ORDER BY version;` sebelum/sesudah bila skema memiliki kolom `version`; jumlah tabel aplikasi tetap.

## Rollback tanpa menghapus volume

1. Jangan hapus volume. Hentikan upgrade jika tes gagal.
2. Pulihkan **source versi sebelumnya** dari arsip `berauload_before_ui_hotfix_*.tar.gz` yang dibuat di atas, ke folder instalasi yang sama; pertahankan `.env` dan data aktif. Pastikan memilih arsip yang dibuat sebelum hotfix.
3. Jalankan `docker compose build && docker compose up -d --no-build` lalu `./deploy/smoke-test.sh` dan `/api/health`.
4. Database tidak berubah karena hotfix ini hanya UI, sehingga rollback **tidak** perlu mengembalikan database dari backup, kecuali Anda melakukan tindakan operasional di luar hotfix.
