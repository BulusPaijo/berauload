# Upgrade BerauLoad V1.4.6.1 → V1.5.0 Tahap 1 (backend saja)

**Status:** Kandidat staging; belum menjadi fitur Topologi lengkap. Tahap 1 hanya menambah dua tabel konfigurasi dan API. Menu/kanvas belum tersedia sampai Tahap 2–4. Jangan pasang patch ini pada versi selain V1.4.6.1.

## Persiapan dan backup

1. Pastikan API `/api/health` masih melaporkan `1.4.6.1`, dan tidak ada pengguna yang sedang mengubah data.
2. Jalankan dari folder instalasi saat ini (contoh `/opt/berauload/BerauLoad_V1_1_1`):

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
```

3. Pastikan arsip SQL dan uploads benar-benar ada dan dapat dibaca. Buat backup source lengkap di luar folder instalasi; cadangkan konfigurasi `.env` secara terpisah dan jaga kerahasiaannya.

```bash
mkdir -p /opt/berauload/source-backups
stamp=$(date +%Y%m%d_%H%M%S)
tar -czf "/opt/berauload/source-backups/source_pre_topology_${stamp}.tar.gz" \
    --exclude='.qa-venv' --exclude='node_modules' --exclude='.git' \
    --exclude='backups' --exclude='.env' -C /opt/berauload BerauLoad_V1_1_1
```

## Uji staging dan pasang

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_5_0_STAGE1_Patch_From_V1_4_6_1.zip -d .
./deploy/test.sh
docker compose build
```

**Jika tes/build gagal: jangan lanjutkan `up`.** Jika lulus, aktifkan secara terencana:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Diharapkan versi API `1.5.0-stage1`. Lihat API melalui browser devtools/curl setelah login; daftar diagram `/api/topology` masih kosong. Tidak ada topologi Berau yang otomatis disemai.

## Validasi penerimaan

- Login akun admin dan pengguna baca-saja masih berfungsi.
- Dashboard, Input Harian, Engineering Rules, Import Excel, dan laporan masih bekerja seperti versi sebelumnya.
- Tes API topologi: non-admin boleh `GET`, tetapi tidak boleh `POST`/`PUT`/`archive`/`restore`; CSRF harus berlaku.
- Semakin banyak topologi tidak boleh menambah baris di `readings` maupun `hour_records`.
- Jam tanpa pembacaan mengembalikan `null`; nilai nol tetap `0`.

## Rollback

1. Jika hanya `docker compose build` yang gagal, kembalikan source dari backup, tanpa menyentuh container atau database.
2. Bila container sudah menjalankan Tahap 1, hentikan deployment baru lalu pulihkan **seluruh source V1.4.6.1**, lakukan `docker compose build && docker compose up -d --no-build`. Jangan menjalankan installer ulang.
3. Migrasi Tahap 1 bersifat *additive*; tabel topologi baru yang tak digunakan aman dibiarkan saat rollback kode. Jangan drop tabel/volume otomatis.
4. Jika diperlukan restore PostgreSQL, gunakan backup SQL yang dipastikan berhasil, dengan prosedur pemulihan tersendiri dan persetujuan administrator. Jangan menghapus volume PostgreSQL.

**Belum diuji pada server LXC produksi Anda**: Docker build, PostgreSQL 16 real, dan browser. Keberhasilan build di server merupakan syarat sebelum dinyatakan layak deploy.
