# Upgrade BerauLoad V1.6.0 Stage 4c UI Hotfix 1 → Stage 5

**Kandidat staging, belum tervalidasi pada PostgreSQL/browser produksi.** Stage 5 menambah tabel `unit_source_changes` (additive) untuk penanda perubahan sumber setelah penguncian ULP; tidak menghapus/mengubah pembacaan lama. **Jangan melakukan upgrade langsung pada production tanpa staging, backup yang dapat di-restore, dan kelulusan build frontend.**

**Baseline yang diharapkan:** `1.6.0-stage4c-ui-hotfix1`. File ZIP Full Source `BerauLoad_V1_6_0_STAGE5_Full_Source.zip` harus diunggah ke `/opt/` LXC. Tidak memakai `down -v`, tidak menghapus `pgdata`/`uploads`.

## Tahapan terminal LXC

```bash
# Selesaikan langkah satu per satu; tidak memakai set -e pada shell SSH interaktif
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
# Simpan salinan source dan .env di luar folder aplikasi
tar -czf "/opt/berauload_before_stage5_$(date +%Y%m%d_%H%M%S).tar.gz" \
  --exclude='./frontend/node_modules' --exclude='./frontend/dist' \
  --exclude='./backups' .

mkdir -p /opt/berauload-stage5-extract
unzip -o /opt/BerauLoad_V1_6_0_STAGE5_Full_Source.zip -d /opt/berauload-stage5-extract
# rsync: apt-get install -y rsync bila belum tersedia
rsync -a --exclude='.env' --exclude='berauload.db' --exclude='backups/' \
  --exclude='uploads/' --exclude='node_modules/' --exclude='dist/' \
  /opt/berauload-stage5-extract/BerauLoad_V1_6_0_STAGE5/ ./
cat VERSION

# Python pada Debian 13 dapat bernama python3, bukan python.
# Untuk tes host, gunakan venv dengan dependency dev dari requirements resmi:
# python3 -m venv /opt/berauload-stage5-qa-venv
# /opt/berauload-stage5-qa-venv/bin/pip install -r backend/requirements-dev.txt
# PYTHONPATH=backend /opt/berauload-stage5-qa-venv/bin/python -m pytest -q backend/tests
# Jika venv lama dan dev dependency tersedia, jalankan perintah Python yang sama lewat venv lama.

node --experimental-strip-types --test frontend/tests/*.test.mjs frontend/src/features/org-units/unitSelection.test.mjs
(cd frontend && npm install && npm run build)
# STOP apabila tes atau npm build gagal! Source tersalin belum berarti container ter-upgrade.

docker compose build
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

## Periksa migrasi PostgreSQL secara baca-saja

```bash
# SELECT saja; jangan melakukan perubahan data dari shell ini
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version FROM schema_migrations WHERE version = '''20261116_16_stage5_source_changes''';"'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM unit_source_changes;"'
```

Setelah startup kedua, periksa lagi jumlah `unit_source_changes`, `readings`, dan `hour_records` **tanpa mengedit data**. Jumlah baris tersebut tidak boleh berubah hanya karena restart. Jangan menjalankan tes yang mengubah database produksi; tes backend memakai SQLite sementara.

## Smoke test peran dan alur browser

1. Admin UP3: pilih ULP, lihat KP-nya dalam pemilih parameter; masuk Formula Builder, simpan formula rekap *dengan operand terlihat*; pilih UP3, lihat hasil computed dan status sumber; pastikan input manual/import UP3 tidak tersedia.
2. Verifier ULP: cek perhitungan dan `n/m`; uji konfirmasi ketika KP draft, lihat audit; setelah ULP final, ubah pembacaan KP dengan akun operator, pastikan nilai ULP terkunci tetapi penanda perubahan tampil bagi verifier/admin. Buka kembali hanya dengan admin dan cek hitung ulang.
3. Operator ULP: bisa mengisi ULP/KP terkait, tidak bisa mengubah konfigurasi. Akun KP: hanya dapat melihat/mengisi KP sendiri, tidak boleh mengakses parameter ULP/UP3/ULP lain.
4. Lihat dashboard, topologi, historical, engineering, Report Builder, Excel/CSV yang menggunakan parameter dari anak. Pastikan unduhan tetap memakai unit terpilih dan informasi sumber tampil. Periksa ULP Tanjung Redeb: angka dan histori historis **harus sama sebelum/selesai** pada jam tidak berubah.
5. Uji PostgreSQL 16, build dan browser pada staging lebih dahulu, kemudian lakukan produksi dengan backup yang dapat diverifikasi.

## Rollback tanpa menghapus volume

1. Jika tes/build gagal **sebelum** `docker compose up`, biarkan container lama berjalan; kembalikan source Stage 4c dari arsip `berauload_before_stage5_*.tar.gz` atau ZIP Stage 4c UI Hotfix 1 (pertahankan `.env` dan volume data).
2. Jika container Stage 5 sudah berjalan, pulihkan source Stage 4c dan jalankan `docker compose build` lalu `docker compose up -d --no-build`; **jangan** gunakan `docker compose down -v` atau hapus `pgdata`/`uploads`.
3. Migrasi Stage 5 hanya menambah tabel; versi lama mengabaikannya. Jika butuh restore DB karena masalah data, gunakan backup yang dibuat sebelum upgrade dan prosedur restore yang sudah terdokumentasi, setelah memastikan dampak pada data yang masuk setelah backup.

**Kejujuran QA:** Build npm yang gagal bukan kelulusan. Pada lingkungan pengembangan, pengujian backend berjalan terhadap SQLite sintetis; belum ada uji browser/PostgreSQL produksi atau bukti bahwa angka produksi ULP Tanjung Redeb identik.
