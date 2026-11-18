# Upgrade BerauLoad 1.6.0 Stage 9a → Stage 9a-fix

**Prasyarat:** Stage 9a sudah terpasang dan berjalan; login/akses serta data ULP Tanjung Redeb tetap memakai sumber Stage 9a. Hotfix ini tidak menambahkan tabel atau migrasi. Jangan pasang langsung jika `docker compose build` atau tes regresi gagal; validasi di staging lebih dulu. Perubahan visual tidak mengganti identitas teknis `BerauLoad` maupun kode internal.

## 1. Backup dan pemeriksaan sebelum menyalin source

Upload `BerauLoad_V1_6_0_STAGE9A_FIX_Full_Source.zip` ke `/opt/` server, kemudian:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
curl -fsS http://127.0.0.1:8092/api/health
# Harus 1.6.0-stage9a sebelum memasang hotfix.
# Simpan backup database+uploads. Bila gagal, HENTIKAN upgrade.
bash ./deploy/backup.sh
# Simpan backup source plus konfigurasi .env:
tar -czf "/opt/berauload_before_stage9a_fix_$(date +%Y%m%d_%H%M%S).tar.gz" \
  --exclude='./backups' --exclude='./frontend/node_modules' --exclude='./frontend/dist' .
```

## 2. Ekstrak dan salin source tanpa mengubah data

```bash
mkdir -p /opt/berauload-stage9a-fix-extract
unzip -o /opt/BerauLoad_V1_6_0_STAGE9A_FIX_Full_Source.zip \
  -d /opt/berauload-stage9a-fix-extract
rsync -a \
  --exclude='.env' --exclude='berauload.db' --exclude='backups/' \
  --exclude='uploads/' --exclude='node_modules/' --exclude='dist/' \
  /opt/berauload-stage9a-fix-extract/BerauLoad_V1_6_0_STAGE9A_FIX/ \
  /opt/berauload/BerauLoad_V1_1_1/
cat VERSION
chmod +x deploy/backup.sh deploy/smoke-test.sh
```

Gunakan versi `1.6.0-stage9a-fix` pada `VERSION`; API masih menjalankan versi lama sampai image baru aktif.

## 3. Pengujian dan build (staging)

Gunakan Python/Node yang benar-benar terpasang; pada LXC Debian host sebelumnya `python`, `node`, dan `npm` tidak tersedia, sehingga pengujian dapat dilakukan di environment Python/Node Docker terpisah dengan source yang sama. Contoh bila tools sudah tersedia:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
PYTHONPATH=backend:. python3 -m pytest -q backend/tests
node --experimental-strip-types --test frontend/tests/*.test.mjs
(cd frontend && npm install --no-audit --no-fund && npm run build)
```

Jika salah satu perintah gagal, jangan deploy. Pengujian tidak boleh diarahkan ke database produksi. `npm install` harus bisa mengakses `registry.npmjs.org` dari lingkungan build.

## 4. Bangun image, jalankan dan smoke test

```bash
cd /opt/berauload/BerauLoad_V1_1_1
docker compose build
docker compose up -d --no-build
docker compose ps
bash ./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Nilai `app` **tetap `BerauLoad`**, `version` menjadi `1.6.0-stage9a-fix`. Jangan pernah menjalankan `docker compose down -v`.

## 5. Pemeriksaan skema dan fungsi

Stage 9a-fix **tidak** membuat migrasi/tabel/kolom baru. Periksa daftar `schema_migrations` sebelum dan sesudah upgrade melalui psql `SELECT version FROM schema_migrations ORDER BY version;` dan pastikan tidak ada versi hotfix baru. Di browser staging: cek tab Pengukuran Gardu, input spreadsheet, master/edit jurusan, duplikasi kode HTTP 409, popup definisi, dan konflik dua pengguna pada gardu/tanggal/sesi sama. Uji peran non-admin tidak dapat mengubah konfigurasi serta verified tetap terkunci.

## 6. Rollback tanpa menghapus volume

1. Pastikan backup sumber dan DB/uploads berhasil dibuat, serta simpan hasilnya di luar container.
2. Pulihkan **source Stage 9a** dari arsip backup source sebelumnya (tanpa menimpa volume dan `.env` kecuali sengaja mengembalikan konfigurasinya).
3. `docker compose build && docker compose up -d --no-build`; cek API health, data master dan pengukuran.
4. Tidak ada migrasi baru yang perlu diturunkan; jangan `DROP`, `down -v`, atau restore DB lama tanpa memahami data yang tercatat setelah upgrade.

**Batas uji:** browser nyata, PostgreSQL 16 dan kelancaran 300 gardu di LXC produksi harus divalidasi sendiri sebelum dinyatakan siap operasional.
