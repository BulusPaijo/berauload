# Upgrade BerauLoad V1.4.2 → V1.4.3

Paket V1.4.3 **kumulatif**: V1.4.2.1 Master Satuan & Formula Unit-Aware + V1.4.3 Advanced Visualization. Tidak perlu memasang dua paket berurutan.

## Syarat

- Versi **aktif** saat ini 1.4.2. Patch ini **bukan** untuk V1.4.1 atau versi lebih lama.
- Docker Compose sehat, PostgreSQL punya ruang penyimpanan cukup, akses LXC dari terminal.
- Sudah mengunduh `BerauLoad_V1_4_3_Update_Patch_From_V1_4_2.zip` dan mengunggah ke `/opt/`.
- Aplikasi memerlukan pemeliharaan terjadwal saat kontainer berganti; hentikan input operator sementara.

## 1. Periksa versi dan cadangkan data

```bash
cd /opt/berauload/BerauLoad_V1_1_1  # sesuaikan dengan direktori aktif Anda
curl -fsS http://127.0.0.1:8092/api/health
# Harus menunjukkan "version":"1.4.2"
docker compose ps
./deploy/backup.sh
ls -lh backups/berauload_*.gz | tail -6
```

Verifikasi kedua backup SQL dan arsip upload **ada dan tidak kosong**. Simpan salinannya di luar LXC sebelum upgrade. Jika backup gagal, **jangan lanjutkan**.

Cadangkan source (tidak menyentuh Docker volumes):

```bash
cd /opt/berauload
cp -a BerauLoad_V1_1_1 "BerauLoad_before_1_4_3_$(date +%Y%m%d_%H%M%S)"
```

Jika direktori aktif Anda tidak bernama `BerauLoad_V1_1_1`, ganti nama pada perintah di atas.

## 2. Pasang patch dan tes sebelum menyalakan kontainer baru

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_4_3_Update_Patch_From_V1_4_2.zip -d .
./deploy/test.sh
docker compose build
```

**Jika unit test atau build gagal, jangan jalankan `up`**. Docker Compose yang aktif belum diganti sampai perintah `up` dijalankan. Hubungi pengelola source untuk memperbaiki error terlebih dahulu.

## 3. Terapkan versi dan verifikasi

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Harus menampilkan version `1.4.3`. Akses aplikasi pada `http://IP-LXC:8092` (atau URL reverse proxy internal yang sudah dikonfigurasi).

## 4. Smoke test melalui browser

1. **Pengaturan → Master Satuan**: daftar kW, MW, kVA, kWh, V, A, %, dst. muncul.
2. Buat satuan custom uji bila perlu; nilai konversi hanya untuk satu dimensi yang sama. Jangan mengubah satuan parameter lama.
3. **Parameter**: dropdown satuan mengambil Master Satuan. Parameter Input baru tetap muncul di tab harian yang dipilih.
4. **Formula Builder**: preview `beban_sistem_kw / daya_pasok_pembangkit_kw * 100` (%) tanpa mengubah formula existing; coba unit yang kompatibel jika ada parameter MW.
5. **Dashboard Builder → Edit Layout → Edit Panel**: ubah warna, legend, desimal, dan pilih MW untuk grafik H/J yang bersatuan kW. Pastikan grafik menunjukkan jumlah yang sama dikonversi (48.000 kW = 48 MW).
6. **Dashboard Utama** mengikuti dashboard default, dan **Batal** di Builder mengembalikan draft lama.
7. Periksa satu hari historis, arsip, perhitungan historis, Engineering Rules, dan status final. Tidak boleh ada nilai input/import berubah akibat upgrade.

## Keamanan data / batasan

- **Jangan** menjalankan `install.sh` ulang, `docker compose down -v`, menghapus `.env`, menghapus volume Postgres, atau mengganti konfigurasi database.
- Tabel baru hanya `unit_definitions`; kode dan satuan asal pada `metrics` maupun `readings` tidak dimigrasikan.
- Konversi pada grafik hanya dilakukan pada salinan data di browser. Data operasional asli tetap identik.
- Satuan bawaan/faktor konversinya terkunci. Satuan custom yang digunakan parameter tidak dapat dinonaktifkan.
- Rumus rekap bawaan H/J dan riwayat report final tidak diubah.
- Tidak ada penetapan ambang teknis PLN otomatis dan tidak ada monitoring SCADA real-time.

## Rollback jika versi baru bermasalah

1. Jangan mencoba `down -v`.
2. Simpan log untuk diagnosis: `docker compose logs --tail=120 backend web`.
3. Untuk regresi UI, source sebelum upgrade dapat dipulihkan dari backup source kemudian `docker compose build && docker compose up -d --no-build`.
4. Database mendapat tabel tambahan `unit_definitions` yang aman dibiarkan saat kembali ke V1.4.2. Data satuan custom yang hanya dikenal V1.4.3 tidak dapat diedit dari V1.4.2.
5. Jika ada masalah data, gunakan prosedur restore resmi dari backup terverifikasi dalam maintenance window. Jangan melakukan reset/restore produksi secara otomatis tanpa pengecekan.
