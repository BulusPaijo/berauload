# BerauLoad V1.5.0 Tahap 1 → Tahap 2 — Single Line Viewer

**Patch ini hanya untuk instalasi yang API-nya sudah `1.5.0-stage1`.** Tahap 2 menambah frontend Mode Lihat dan memperbarui nomor versi. Tidak menambah tabel/migrasi, tidak menulis pembacaan, dan tidak menghapus data lama.

## 1. Backup dahulu

Pada LXC, jalankan dari folder source aktif (sesuaikan jika berbeda):

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
```

Pastikan `version` benar-benar `1.5.0-stage1`, backup SQL & uploads sukses, dan simpan backup source **di luar** folder proyek agar tidak ikut tertimpa:

```bash
mkdir -p /opt/berauload/source-backups
stamp=$(date +%Y%m%d_%H%M%S)
tar -czf "/opt/berauload/source-backups/source_pre_stage2_${stamp}.tar.gz" \
  --exclude='.qa-venv' --exclude='node_modules' --exclude='backups' \
  --exclude='.git' --exclude='.env' -C /opt/berauload BerauLoad_V1_1_1
```

`.env` dan berkas rahasia harus tetap berada pada tempatnya, dengan izin file terbatas. Simpan backup konfigurasi terpisah apabila diperlukan.

## 2. Patch dan tes

Unggah `BerauLoad_V1_5_0_STAGE2_Patch_From_STAGE1.zip` ke `/opt/` via WinSCP, lalu:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_5_0_STAGE2_Patch_From_STAGE1.zip -d .
./deploy/test.sh
node --test frontend/tests/topologyViewer.test.mjs
docker compose build
```

**Hentikan proses jika satu tes atau build gagal.** Jangan jalankan installer, jangan menghapus `.env`, volume database, atau berkas hasil import.

## 3. Aktifkan jika semua lulus

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Versi seharusnya `1.5.0-stage2`. Lakukan Ctrl+Shift+R lalu buka **Monitoring → Topologi**. Pada instalasi tanpa konfigurasi diagram, **kanvas kosong adalah hasil yang benar**, bukan kegagalan upgrade.

## 4. Pemeriksaan penerimaan

- Login admin, operator/manajemen dan lihat menu Topologi. Tidak ada tombol mengoperasikan pemutus.
- Periksa selector diagram: bila belum ada, tampil pesan kosong yang jelas dan **tidak** ada topologi dummy.
- Uji bilah tanggal/jam, Putar/Jeda, dan zoom. Teks harus menampilkan jam WITA.
- Jika sudah ada diagram terverifikasi, cocokkan nilai kotak terhadap Data Historis pada hari/jam yang sama. Nilai kosong tetap `—` dan angka nol tetap `0`.
- Klik kotak parameter untuk membuka grafik 24 jam; tidak boleh ada garis melompati jam tanpa data.
- Verifikasi Dashboard, Input Beban Harian, Import Excel, Formula Engine, Engineering Rules, Laporan dan Export tetap bekerja.

## 5. Rollback tanpa menghapus volume

Jika build gagal, kembalikan source dari backup **tanpa** menjalankan `docker compose up`. Jika sudah diaktifkan dan ditemukan masalah, pulihkan source Tahap 1 beserta berkas konfigurasi tetap; build image lama, lalu `docker compose up -d --no-build`. Tidak ada skema baru pada Tahap 2 sehingga rollback source tidak memerlukan rollback database. Jangan jalankan `docker compose down -v` dan jangan menjalankan installer ulang.

Tahap 2 baru teruji offline pada regresi backend, tes pure JS dan sintaks TypeScript. Validasi Docker Compose/PostgreSQL/browser aktual harus dilakukan di LXC.
