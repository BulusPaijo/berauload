# Upgrade BerauLoad V1.5.0 Tahap 3 → Tahap 4 (Diagram Builder Lengkap)

**Khusus server dengan API `1.5.0-stage3`.** Upgrade menambah palet simbol dan jalur manual pada konfigurasi Topologi. Tahap 4 **tidak menambah tabel/migrasi database**, tidak menulis `readings` atau `hour_records`, dan tidak mengubah rumus kelistrikan. Semua diagram lama tetap dipakai.

## 1. Backup wajib sebelum overlay

Di Debian LXC (gunakan direktori instalasi aktual):

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
```

Pastikan versi `1.5.0-stage3`, backup SQL dan uploads sukses. Cadangkan source **terpisah** dari direktori yang akan di-overlay:

```bash
mkdir -p /opt/berauload/source-backups
stamp=$(date +%Y%m%d_%H%M%S)
tar -czf "/opt/berauload/source-backups/source_pre_stage4_${stamp}.tar.gz" \
 --exclude='.qa-venv' --exclude='node_modules' --exclude='backups' \
 --exclude='.git' --exclude='.env' -C /opt/berauload BerauLoad_V1_1_1
```

Jaga `.env` tetap di server; jangan membagikan credential atau backup database.

## 2. Upload patch dan jalankan tes sebelum aktivasi

Upload `BerauLoad_V1_5_0_STAGE4_Patch_From_STAGE3.zip` ke `/opt/` melalui WinSCP, lalu:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_5_0_STAGE4_Patch_From_STAGE3.zip -d .
./deploy/test.sh
node --test frontend/tests/topologyViewer.test.mjs \
  frontend/tests/topologyEditor.test.mjs frontend/tests/topologyStage4.test.mjs
docker compose build
```

**Jangan lanjut jika satu langkah gagal.** Build `web` wajib berhasil menjalankan `npm install` dan `npm run build` TypeScript/Vite dengan dependensi asli. Tes offline pembangunan Stage 4 belum dapat menyelesaikan build npm karena registry tidak dapat diakses.

## 3. Aktivasi dan smoke test

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Versi API yang diharapkan `1.5.0-stage4`. Semua service wajib sehat. Buka ulang browser memakai **Ctrl+Shift+R**.

## 4. Tes penerimaan di browser

1. Admin → Monitoring → Topologi → Diagram Baru (tetap kanvas kosong) → Edit Diagram.
2. Dari palet tambah 8 jenis simbol satu per satu; gunakan klik pada kanvas dan seret dari palet, pindahkan/rotasi/ubah label secara manual. PMT harus hanya simbol netral.
3. Pilih Gambar Garis, pilih level visual, buat garis dengan 2–4 titik, klik Selesaikan Garis. Pilih garis dalam Mode Pilih/Geser, geser vertex, tambah vertex, hapus vertex/garis. Jangan ada sambungan otomatis.
4. Tambah kotak Ringkasan/Peringkat/Legenda/Teks dan kotak Parameter; pilih nama/sumber/metric dan coba snap/drag. Peringkat harus menolak gabungan satuan berbeda; legenda tidak mengklaim status peralatan.
5. Aktifkan Grafik Mini, pilih tanggal/jam WITA; cek NULL tampil `—`, angka 0 tetap `0`, celah histori tidak dihubungkan oleh garis.
6. Coba Urungkan/Ulangi, Reset/Batal lalu Simpan. Refresh; lokasi/simbol/garis tetap. Uji Riwayat Revisi dan konflik perubahan paralel HTTP 409.
7. Login non-admin: dapat Mode Lihat saja. Periksa tidak ada tombol untuk mengoperasikan pemutus.
8. Uji regresi input, import Excel REKAP H/J, grafik dashboard, Formula Engine, Engineering Rules, laporan, dan riwayat pembacaan.

## 5. Rollback tanpa menghapus data

Jika build gagal, **jangan aktifkan** image baru. Jika sudah diaktifkan tetapi bermasalah: pulihkan source dari arsip yang dibuat di langkah 1 (contoh `tar -xzf /opt/berauload/source-backups/source_pre_stage4_<stamp>.tar.gz -C /opt/berauload`), pastikan `.env` tetap utuh; lalu jalankan:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
docker compose build
docker compose up -d --no-build
./deploy/smoke-test.sh
```

Ini mengembalikan **source/image Tahap 3**. Jangan memakai `docker compose down -v`, `install.sh` ulang, atau menghapus volume PostgreSQL. Diagram yang telanjur disimpan dengan objek Tahap 4 tidak otomatis dihapus oleh rollback; API Tahap 3 sudah mengenal struktur layout dan tetap dapat membacanya, sementara beberapa gaya visual baru tidak akan tampil selengkap Tahap 4. Buat salinan atau revisi sebelum rollback bila ada layout baru penting.

**Status paket:** kandidat staging hingga `docker compose build`, pengujian PostgreSQL asli dan browser LXC selesai dengan sukses. Lihat `QA_STATUS.md`.
