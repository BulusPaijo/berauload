# Upgrade BerauLoad Stage 9b → 1.6.0-stage9c-fix

**Kandidat staging: jangan langsung jalankan pada produksi sebelum pengujian PostgreSQL 16 dan browser LXC.** Paket ini adalah **full source kumulatif**: tidak perlu memasang Stage 9c awal dahulu. Versi database lama Stage 9b dapat dinaikkan langsung; migrasi Stage 9c dijalankan otomatis saat startup, aditif dan tercatat dalam `schema_migrations`. Hotfix ini **tidak membuat migrasi atau mengubah data ukur 9a dan rumus/seed 9b**.

## Perintah upgrade langsung dari Stage 9b

1. Upload `BerauLoad_V1_6_0_STAGE9C_FIX_Full_Source.zip` dan `upgrade_stage9b_to_stage9c_fix.sh` (disertakan juga di ZIP pada `deploy/`) ke direktori `/opt/` pada LXC melalui WinSCP/SCP.
2. Pastikan sistem sedang pada `1.6.0-stage9b`, database `db` dan `backend` sehat, tersedia ruang untuk backup database, source, dan seluruh uploads. Jalankan terlebih dahulu di staging yang menggunakan salinan database produksi.
3. Perintah di SSH LXC:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
unzip -tq /opt/BerauLoad_V1_6_0_STAGE9C_FIX_Full_Source.zip
bash /opt/upgrade_stage9b_to_stage9c_fix.sh
```

Lokasi berbeda dapat disetel tanpa mengubah file:

```bash
APP_DIR=/opt/berauload/BerauLoad_V1_1_1 \
ZIP_FILE=/opt/BerauLoad_V1_6_0_STAGE9C_FIX_Full_Source.zip \
bash /opt/upgrade_stage9b_to_stage9c_fix.sh
```

Skrip menolak versi selain `1.6.0-stage9b`, memeriksa ZIP, mewajibkan backup `pg_dump -Fc` (dan memverifikasi arsip dengan `pg_restore --list`), backup seluruh uploads dari volume backend, dan backup source termasuk `.env` sebelum overlay. `rsync` tidak menghapus file, tidak menimpa `.env`/uploads/backups, serta menjalankan `docker compose build backend web` sebelum `docker compose up -d --no-build`. Cadangan disimpan pada `backups/upgrade_stage9c_fix_<tanggal-jam>/` dan SHA256 dicatat. Pastikan backup juga disalin keluar LXC. Skrip memerlukan `unzip`, `rsync`, `tar`, `curl`, `docker`, dan `sha256sum`.

**Peringatan:** skrip yang membuat backup tidak otomatis mengembalikan kode lama bila build/deployment gagal. Gunakan rollback di bawah. Volume database dan uploads tidak dihapus. Jangan menggunakan `docker compose down -v`.

## Pemeriksaan hasil

```bash
cd /opt/berauload/BerauLoad_V1_1_1
docker compose ps
docker compose logs --tail=150 backend web
curl -fsS "http://127.0.0.1:${APP_PORT:-8092}/api/health"
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 10;"'
```

`/api/health` diharapkan memuat `"app":"BerauLoad"` dan `"version":"1.6.0-stage9c-fix"`. Periksa tabel `gardu_analysis_views`, `gardu_analysis_settings`, indeks Stage 9c dan tidak ada perubahan pada tabel pembacaan lama. Jalankan restart backend kedua kali di staging untuk memeriksa idempotensi migrasi.

### Smoke test fungsional (akun yang berhak)

- Menu **Pengukuran Gardu → Analisa**: cari beberapa gardu yang mempunyai 3+ pengukuran dan filter `total_r` dengan ≥, ≤, antara, kosong, ada. Baris dengan nilai 0 harus ikut `>= 0` dan `<= 0`; NULL tidak ikut operator angka.
- Pada temuan, pilih dua aturan: `Salah satu temuan (any)` dan `Semua temuan (all)`; nilai `total`, ringkasan, file CSV/XLSX harus sesuai dan URL memuat `findings=a&findings=b`. Coba `?findings=a,b` dengan kode nyata.
- URL salah, misalnya `?numeric_code=total_r&numeric_op=gte` atau `?findings=nope` harus HTTP 422 (setelah login), bukan HTTP 500. Pilih kolom kustom admin setelah penghitungan ulang selesai.
- Ulangi filter gabungan kategori, temuan, kolom angka, sesi dan sortir; periksa hak akses unit, hasil verified/final, dan tidak ada perubahan data ukur.
- Uji browser desktop dan ponsel. Buktikan concurrency recalc/save dan benchmark di PostgreSQL 16 bila hendak mengaktifkan di produksi. `EXPLAIN (ANALYZE, BUFFERS)` pada data staging yang menyerupai produksi; catat hasilnya sebelum mengklaim target performa.

## Rollback kode (tanpa menghapus volume)

1. Hentikan aktivitas tulis operator, periksa apakah ada data sah baru sejak backup; **jangan otomatis me-restore dump karena akan menghilangkan data yang masuk kemudian**.
2. Temukan folder `backups/upgrade_stage9c_fix_<timestamp>/` yang benar, kemudian:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
BACKUP=/opt/berauload/BerauLoad_V1_1_1/backups/upgrade_stage9c_fix_<timestamp>
test -s "$BACKUP/source.tar.gz"
tar -xzf "$BACKUP/source.tar.gz" -C /opt/berauload/BerauLoad_V1_1_1
test "$(cat VERSION)" = '1.6.0-stage9b'
docker compose build backend web
docker compose up -d --no-build
docker compose ps
```

Skema Stage 9c aditif sehingga source 9b mengabaikan tabel baru; jangan DROP tabel, jangan hapus volume. Bila memerlukan restore database sesudah integritas diperiksa, rencanakan downtime dan gunakan prosedur DBA dari cadangan tervalidasi setelah memeriksa kemungkinan perubahan data terbaru.

## Batas validasi paket

Di lingkungan build ini **tidak tersedia server PostgreSQL 16/driver/daemon Docker**; SQL PostgreSQL hanya dapat dikompilasi, bukan dieksekusi. `npm install` gagal `EAI_AGAIN registry.npmjs.org`, sehingga `npm run build` gagal karena dependency React/types tidak tersedia; error TypeScript yang terdeteksi setelah percobaan build dicatat dalam `QA_STATUS_STAGE9C_FIX.md`. Build Docker berhasil/gagal baru dapat ditentukan di LXC. Tidak ada klaim lolos browser atau PostgreSQL.
