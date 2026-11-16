# BerauLoad V1.1.2 — Update Patch dari V1.1.1

Paket ini **bukan full installer**. Hanya overlay file yang berubah, termasuk modul migrasi additive dan UI.

1. Pastikan V1.1.1 sudah terpasang dan memiliki grafik H/J (termasuk hotfix TS2531), kemudian jalankan `./deploy/backup.sh` di direktori aktif. Periksa backup.
2. Upload ZIP patch ke `/opt/` lalu ekstrak **dari folder root aktif**:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_1_2_Update_Patch.zip -d .
docker compose build
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
```

3. Cek `/api/health` versi `1.1.2`, Pengaturan → Parameter (drawer), Dashboard → Pilih Parameter dan default sistem/personal.

**Wajib:** jangan jalankan installer ulang, `docker compose down -v`, atau hapus `.env`/volume database/upload. Jika folder aktif Anda berbeda, ganti `cd` sesuai lokasi. Build Docker/TypeScript end-to-end belum dapat diuji di lingkungan pengembangan; uji dahulu di staging.
