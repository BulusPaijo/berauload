# Upgrade BerauLoad V1.2.0 → V1.3.0 (termasuk V1.2.1)

**Prasyarat:** versi yang berjalan benar-benar `1.2.0`. Patch ini hanya dijamin untuk source V1.2.0 yang telah ditetapkan sebagai baseline. Jika server masih V1.1.x, upgrade dulu ke V1.2.0. Jangan jalankan installer ulang.

## 1. Pemeriksaan dan backup

1. Unggah `BerauLoad_V1_3_0_Update_Patch_From_V1_2_0.zip` ke `/opt/` melalui WinSCP.
2. Login SSH ke LXC dan masuk **folder BerauLoad yang saat ini aktif**, tidak harus bernama V1.2.0:

```bash
cd /opt/berauload/BerauLoad_V1_1_1 # SESUAIKAN dengan direktori aktif Anda
pwd
curl -fsS http://127.0.0.1:8092/api/health
docker compose ps
./deploy/backup.sh
ls -lh backups/berauload_*.gz | tail -4
```

Harus terlihat `version: 1.2.0` dan dua file backup terbaru (PostgreSQL serta uploads) berukuran masuk akal. Salin backup terenkripsi ke lokasi terpisah bila ada kebijakan retensi organisasi. Jangan unggah `.env`, database, atau file Excel operasional ke percakapan publik.

3. Simpan source rollback (folder `backups` dikecualikan agar tidak menggandakan):

```bash
mkdir -p /opt/berauload_source_backup
umask 077
tar -czf /opt/berauload_source_backup/source_before_v1_3.tar.gz \
  --exclude='./backups' --exclude='./frontend/node_modules' \
  --exclude='./.qa-venv' .
```

## 2. Terapkan patch, build sebelum restart

```bash
unzip -o /opt/BerauLoad_V1_3_0_Update_Patch_From_V1_2_0.zip -d .
cat VERSION  # 1.3.0

docker compose build
docker compose up -d --no-build

docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
docker compose logs --tail=100 backend web
```

Jika `APP_PORT` berbeda, ubah port pada perintah `curl`. **Jangan** gunakan `docker compose down -v`, `docker volume rm`, atau menghapus database. Build frontend yang gagal tidak perlu diikuti `up`.

## 3. Uji penerimaan di browser

1. Login admin → `Analisis Beban → Perhitungan Historis`, pilih formula lama V1.2.0. Pastikan hasil sama dengan sebelum upgrade.
2. Klik `Edit / Revisi`, ubah contoh formula dengan alasan revisi. Periksa versi bertambah dan `Riwayat versi` tetap dapat menjalankan versi sebelumnya.
3. Klik `Arsipkan`, periksa formula tidak bisa dijalankan sebagai formula aktif; pilih versi historis untuk audit, lalu `Pulihkan`.
4. Buka `Analisis Beban → Engineering Rules`. Buat aturan uji dengan parameter H/J, **ambang hanya dari keputusan teknis Anda** dan catat dasar ketentuannya. Uji contoh angka, simpan draft, lalu aktifkan dengan alasan.
5. Evaluasi periode dengan beberapa jam belum diisi. Jam hilang **tidak** boleh dihitung sebagai normal. Setelah revisi aturan, status kembali draft.
6. Cek Dashboard grafik **Daya Mampu kolom H vs Beban Sistem kolom J**, Input Beban, Import Excel, Formula Builder V1.1, serta export laporan. Data lama tidak boleh berubah.

## 4. Rollback

Jika frontend gagal build, berhenti: **jangan jalankan** `up`. Pulihkan source dari arsip sebelum V1.3 lalu jalankan build ulang. Jika container sudah sempat berjalan, tabel/kolom baru bersifat **additive**; backend lama boleh mengabaikannya. Rollback source saja tidak otomatis membatalkan definisi Rule atau revisi formula baru; catat perubahan yang dibuat setelah upgrade. Restore database secara penuh hanya dilakukan dari backup tervalidasi dan melalui prosedur pemulihan terencana.

## 5. Batasan versi

- Perhitungan versi lama dapat dijalankan eksplisit; dashboard/laporan V1 yang sudah final **tidak diubah** oleh migrasi. Perhitungan Historis bersifat **on-demand**, belum menyimpan snapshot final hasil kalkulasi.
- Engineering Rules V1.3.0 hanya **evaluasi advisory historis**, bukan alarm/paging real-time, otomatisasi SCADA, atau kendali peralatan.
- Tidak ada ambang operasi default. Hanya admin yang dapat membuat/menyetujui aturan. Data tidak tersedia dihitung sebagai incomplete, tidak dinyatakan normal.
- Engine membatasi evaluasi Engineering Rules maksimum 366 hari per permintaan. Untuk agregasi multi-tahun gunakan modul Historis V1.2.
- Tes offline backend telah dilakukan menggunakan SQLite QA, **bukan Docker/PostgreSQL/LXC aktual**. Lakukan staging, backup, serta uji browser di server sebelum menerima sebagai production.
