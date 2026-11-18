# Upgrade BerauLoad Stage 9b → 1.6.0-stage9c

**KANDIDAT STAGING — jangan langsung production.** Install dependency frontend, `npm run build`, migrasi PostgreSQL 16 nyata, browser, dua hitung ulang serentak dan kinerja 200/100.000 pengukuran **belum terverifikasi pada LXC**. Source lama dan data produksi harus dibackup.

## Persiapan

Pastikan container `db` PostgreSQL 16 sehat, semua perubahan 9b telah diterapkan, dan file ZIP ada di LXC. Sesuaikan lokasi `APP` dan `ZIP` berikut dengan lingkungan riil. Contoh dari percakapan sebelumnya:

```bash
set -euo pipefail
APP=/opt/berauload/BerauLoad_V1_1_1
ZIP=/opt/BerauLoad_V1_6_0_STAGE9C_Full_Source.zip
NOW=$(date +%Y%m%d_%H%M%S)
cd "$APP"
test -f "$ZIP" && test -f .env && test "$(cat VERSION)" = '1.6.0-stage9b'
unzip -tq "$ZIP"
docker compose ps

# Cadangan PostgreSQL format custom dan source; verifikasi keduanya.
mkdir -p backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "backups/before_stage9c_${NOW}.dump"
test -s "backups/before_stage9c_${NOW}.dump"
tar -czf "/opt/berauload_source_before_stage9c_${NOW}.tgz" \
  --exclude='./backups' --exclude='./frontend/node_modules' \
  --exclude='./frontend/dist' .

TEMP=$(mktemp -d)
unzip -q "$ZIP" -d "$TEMP"
rsync -a --exclude='.env' --exclude='backups/' --exclude='uploads/' \
  --exclude='*.db' --exclude='node_modules/' --exclude='dist/' \
  "$TEMP/BerauLoad_V1_6_0_STAGE9C/" "$APP/"
cat VERSION
docker compose config -q
# Build harus selesai sebelum mengganti container lama.
docker compose build
docker compose up -d --no-build
docker compose ps
bash deploy/smoke-test.sh
curl -fsS "http://127.0.0.1:${APP_PORT:-8092}/api/health"
```

**Jangan gunakan `docker compose down -v`.** Salin arsip backup ke lokasi lain sebelum upgrade. Untuk file uploads gunakan juga backup volume yang terverifikasi. Gunakan staging dari salinan database produksi dan jangan menguji rumus teknik pada data resmi.

## Pemeriksaan migrasi

Setelah backend mulai, gunakan `psql` melalui container DB:

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT version FROM schema_migrations;"'
```

Periksa juga tabel `gardu_analysis_views` dan `gardu_analysis_settings`, serta indeks `ix_gardu_analysis_measured_date` dan `ix_gardu_analysis_match_code` melalui `\di`/`pg_indexes`. Menjalankan startup dua kali tidak boleh menggandakan seed, memindahkan data, atau menimpa tampilan admin. Konfigurasi acuan awal diambil dari `persen_beban` jika ada. Hasil ukur 9b yang versi lama diproses via menu **Rumus & Kategori → Hitung ulang / lanjutkan** sampai selesai.

## Smoke test setelah upgrade

1. Masuk sebagai admin; buka Pengukuran Gardu → Rumus & Kategori. Buka dua browser dan jalankan hitung ulang bersamaan: tidak boleh ada HTTP 500/duplikasi; yang sibuk menampilkan *mencoba lagi*.
2. Simpan draft pengukuran lain bersamaan dengan hitung ulang; pastikan kedua sisi tidak 500, data ukur dan status verified utuh. Uji lagi di staging.
3. Periksa `/test` dan `/preview` untuk siklus, dan untuk jurusan 3 pada gardu 2-jurusan; harus 422 untuk siklus, sementara jurusan tidak ada diberi catatan, bukan 0.
4. Buka tab Analisa; uji mode Terakhir/Periode/Semua, kategori, angka 0 vs NULL, sesi, sortir NULL terakhir, halaman berikutnya, tampilan pribadi/bersama, hasil ukuran verified.
5. Unduh CSV dan XLSX, periksa tab **Keterangan** dan keamanan sel formula berawalan `=`, `+`, `-`, `@`. Periksa juga akses management/kantor lain.
6. Jalankan `npm install && npm run build` di staging, cek UI browser desktop/ponsel dan `docker compose logs --tail=150 backend web`.
7. Jalankan `EXPLAIN (ANALYZE, BUFFERS)` atas SQL query yang dihasilkan untuk data 5.000 gardu/100.000 kunjungan; ukur ulang 200 kunjungan dan bulk 200 secara berulang pada PostgreSQL lokal. Belum ada angka benchmark produksi yang bisa dipercaya.

## Rollback tanpa menghapus volume

Jika smoke test gagal, hentikan transaksi dan simpan log, kembalikan arsip source 9b, lalu `docker compose build && docker compose up -d --no-build`. Skema 9c aditif dan diabaikan source 9b; jangan DROP tabel dan jangan hapus volume. Jangan otomatis restore dump jika operator sudah menginput data baru sesudah backup—restore penuh menghapus perubahan tersebut. Putuskan prosedur restore berdasarkan backup terverifikasi dengan mempertimbangkan data selama downtime.
