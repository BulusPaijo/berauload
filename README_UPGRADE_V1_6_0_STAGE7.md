# Upgrade BerauLoad V1.6.0 Stage 6 → Stage 7

**STATUS: KANDIDAT STAGING; bukan rilis yang sudah lulus build frontend.**
Source Stage 7 mengubah operasi input, sesi, dan satu migrasi aditif. Backup database,
file uploads, dan source yang berjalan **sebelum** menyalin paket. Jangan menguji
beban pada produksi.

## 1. Siapkan clone staging terlebih dahulu

Gunakan PostgreSQL 16 volume *berbeda* dan port berbeda; staging boleh memakai
salinan backup produksi bila kebijakan kerahasiaan mengizinkan, tetapi loadtest
synthetic fixture hanya untuk DB pengujian yang kosong. Uji waktu/session/akses
browser sebelum pemasangan produksi. Tidak ada perubahan isi data historis oleh
migrasi ini, tetapi penghapusan sesi kedaluwarsa adalah pekerjaan maintenance
terpisah yang dilakukan saat startup.

```bash
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
# Simpan source beserta .env; arsip ini untuk rollback source saja.
tar -czf /opt/berauload_pre_stage7_$(date +%Y%m%d_%H%M%S).tar.gz \
  --exclude='./backups' --exclude='./frontend/node_modules' \
  --exclude='./frontend/dist' .
mkdir -p /opt/berauload-stage7-extract
unzip -o /opt/BerauLoad_V1_6_0_STAGE7_Full_Source.zip \
  -d /opt/berauload-stage7-extract
rsync -a --exclude='.env' --exclude='berauload.db' \
  --exclude='backups/' --exclude='uploads/' \
  --exclude='node_modules/' --exclude='dist/' \
  /opt/berauload-stage7-extract/BerauLoad_V1_6_0_STAGE7/ \
  /opt/berauload/BerauLoad_V1_1_1/
cat VERSION
```

Sebelum upgrade produksi pastikan `cat VERSION` pada server sebelumnya adalah
`1.6.0-stage6` dan Stage 6 yang berjalan sudah tervalidasi. Jangan melakukan
upgrade dari Stage 4c langsung ke Stage 7 tanpa menguji tahap perantaranya.

## 2. Validasi source sebelum mengganti container

```bash
cd /opt/berauload/BerauLoad_V1_1_1
# Jika host Debian tidak memiliki perintah `python`, gunakan virtualenv QA:
python3 -m venv /opt/berauload-stage7-qa
/opt/berauload-stage7-qa/bin/pip install -r backend/requirements-dev.txt
PYTHONPATH=backend /opt/berauload-stage7-qa/bin/python \
  -m pytest -q backend/tests
node --experimental-strip-types --test frontend/tests/*.test.mjs
(cd frontend && npm install && npm run build)
```

**Stop jika tes atau build gagal.** `npm run build` harus lulus di staging yang
mempunyai akses registry; tes Node/kompilasi sintaks bukan penggantinya.

## 3. Variabel baru (semua opsional, tetap bawaan bila tidak diatur)

| Variabel | Bawaan | Fungsi |
|---|---:|---|
| SESSION_HOURS | 12 | Batas sesi bergeser ketika digunakan |
| SESSION_MAX_HOURS | 24 | Batas mutlak sejak login |
| UVICORN_WORKERS | 1 | Hanya 1 diizinkan Stage 7 |
| DB_POOL_SIZE | 5 | Koneksi dasar per worker |
| DB_MAX_OVERFLOW | 5 | Koneksi tambahan per worker |
| DB_POOL_TIMEOUT | 30 | Waktu tunggu koneksi dalam detik |
| DB_POOL_RECYCLE | 1800 | Recycle koneksi dalam detik |
| BERAULOAD_TEST_INSTANCE | false | Hanya true pada instans loadtest terpisah |

Rumus batas: `workers × (DB_POOL_SIZE + DB_MAX_OVERFLOW) + koneksi_cadangan
< max_connections` PostgreSQL. Contoh 1 × (5 + 5) + 20 = 30, harus lebih kecil
dari `max_connections`. Nilai tidak sah ditolak saat startup. Jangan mengubah
`UVICORN_WORKERS` di atas 1; invalidasi cache dan migrasi lintas worker belum
memiliki bukti pengujian yang cukup. Jangan menaikkan worker untuk mencoba
mengatasi bottleneck secara spekulatif.

## 4. Build, deploy, dan smoke test (setelah semua tes dan build lulus)

```bash
cd /opt/berauload/BerauLoad_V1_1_1
docker compose build
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Harapan: `/api/health.version == 1.6.0-stage7`; `backend` dan `db` healthy;
`web` healthy/started. Browser: admin, operator, verifier, management, KP;
input 0 dan kosong; edit dua browser/dua parameter; edit sama menghasilkan
409 dan pilihan; putus jaringan; logout/session expiry dan login ulang dengan
akun yang sama; import lama/template; verified/final tetap terkunci; cek
formula KP→ULP→UP3 dan angka historis ULP Tanjung Redeb sebelum/sesudah.

## 5. Pemeriksaan migrasi baca-saja setelah deploy

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
"SELECT version FROM schema_migrations WHERE version = '\''20261116_17_stage7_session_safety'\'';"'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
"SELECT column_name FROM information_schema.columns WHERE table_name = '\''login_sessions'\'' AND column_name = '\''last_seen_at'\'';"'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
"SELECT COUNT(*) FROM login_attempts;"'
```

Migrasi ini menambahkan `login_sessions.last_seen_at` nullable dan tabel
`login_attempts` (dengan indeks pencarian). Tidak melakukan DROP/ubah tipe,
tidak backfill pembacaan historis; migrasi hanya sekali melalui
`schema_migrations`. Startup membersihkan **sesi kedaluwarsa** secara sengaja,
tidak menghapus pembacaan, formula, riwayat, atau status hari.

## 6. Uji beban hanya di instans tes

Baca `deploy/loadtest/README.md`. Gunakan compose project
`berauload-stage7-loadtest`, port 18092/18093 dan volume terpisah. Jangan
menjalankan `deploy/loadtest/runner.py` terhadap port produksi 8092. Pengujian
20 pengisi + 60 pembaca/5 menit dan penilaian p95 mesti dilakukan di LXC
staging PostgreSQL sebelum kapasitas dianggap lulus.

## 7. Rollback tanpa menghapus volume

Jika deployment Stage 7 tidak sehat, hentikan traffic pengisian pada aplikasi
staging/produksi yang terdampak, dokumentasikan kondisi transaksi, lalu
pulihkan **source yang sebelumnya dicadangkan** menggunakan arsip
`/opt/berauload_pre_stage7_*.tar.gz` yang benar. Restore menggunakan `rsync`
atau `tar` setelah mengekstrak ke direktori sementara dan memverifikasi isinya;
jangan menimpa `.env` atau uploads jika konfigurasi terbaru harus dipertahankan.
Kemudian `docker compose build`, `docker compose up -d --no-build`, dan smoke
check versi lama. **Jangan `docker compose down -v`.** Kolom dan tabel baru
aditif sehingga source Stage 6 dapat mengabaikannya; backup database tetap
penting jika membutuhkan pemulihan penuh. Jangan rollback database tanpa
persetujuan dan audit untuk pembacaan yang terjadi setelah upgrade.
