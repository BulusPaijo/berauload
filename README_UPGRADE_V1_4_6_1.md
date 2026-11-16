# Upgrade BerauLoad V1.4.6 → V1.4.6.1

**Scope hanya Laporan Standar — Perbandingan Parameter Antar-Tahun.** Paket ini **khusus sumber V1.4.6 yang sudah terpasang**. Laporan Kustom, Dashboard Builder, Formula Engine dan seluruh data pengukuran tetap dipertahankan. Tidak diperlukan installer ulang atau perubahan `.env`.

## 1. Validasi sebelum upgrade

Jalankan di folder BerauLoad yang sudah aktif pada LXC (contoh `/opt/berauload/BerauLoad_V1_1_1`):

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
```

Pastikan versi **1.4.6**. Jika bukan 1.4.6, jangan pasang patch ini. Pastikan tidak ada proses input/import berjalan; hentikan aktivitas operasional sementara sesuai prosedur.

## 2. Backup

```bash
./deploy/backup.sh
# Tinjau file backup SQL + uploads dan cadangkan di lokasi lain.
# Cadangkan juga seluruh source aplikasi, termasuk berkas tersembunyi, ke lokasi privat.
```

**Dilarang** menghapus volume Docker, menjalankan `docker compose down -v`, membagikan `.env`, atau menjalankan `install.sh` untuk upgrade.

## 3. Pasang patch & uji sebelum aktif

Unggah `BerauLoad_V1_4_6_1_Update_Patch_From_V1_4_6.zip` ke `/opt/`, lalu:

```bash
unzip -o /opt/BerauLoad_V1_4_6_1_Update_Patch_From_V1_4_6.zip -d .
./deploy/test.sh
docker compose build
```

Lanjutkan **hanya jika seluruh tes dan build selesai tanpa error**:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Versi yang diharapkan adalah `1.4.6.1`.

## 4. Migrasi dan dampak

- Migration additive/idempotent membuat tabel `standard_report_selections` untuk preferensi laporan sistem/pribadi.
- Tabel `readings`, `hour_records`, status final, formula, dan seluruh master tidak berubah.
- Endpoint lama `/api/compare?year_a=2025&year_b=2026` **tetap tersedia** dan default menggunakan maksimum (`max`). Field hasil lama `peak`, `avg`, `hours`, `peak_growth_pct`, `comparable` tetap ada; tambahan `min`, `value_a`, `value_b`, `growth_pct`, dan `aggregation` tidak mengubah hasil lama.
- Parameter Input/Computed dapat dipilih jika aktif; jika pembacaan computed belum tersimpan maka hasil kosong, bukan dibuat otomatis.

## 5. Uji penerimaan browser

1. Buka **Laporan & Perbandingan → Laporan Standar**, cari kartu **Perbandingan Parameter Antar-Tahun**.
2. Klik **Pilih Parameter** dan ganti dari Beban Sistem menjadi **Daya Mampu Sistem (kolom H)**. Pastikan grafik/tabel dan satuan mengikuti pilihan.
3. Pilih metode **Maksimum**, **Rata-rata**, dan **Minimum**. Periksa nilai salah satu bulan terhadap Analisis Beban. Bulan yang hilang harus tetap `—`.
4. Ubah tahun pembanding, misalnya 2025 vs 2026. Bulan dengan jam belum lengkap harus bertanda **Parsial/tidak ada**.
5. **Simpan Pilihan Saya**, refresh, pastikan preferensi bertahan. Admin dapat **Jadikan Default Sistem**; pengguna lain mengikuti default kecuali memiliki preferensi pribadi.
6. Tekan **Reset Pribadi** untuk kembali mengikuti default sistem.
7. Periksa tab **Laporan Kustom**, Export Data, Dashboard Builder, Input Beban Harian, dan grafik H/J: semuanya tetap berfungsi.

Catatan: hanya **satu parameter** dapat dibandingkan pada grafik ini untuk menjamin satuan yang konsisten. Nilai agregat dihitung dari jam yang tercatat; persentase perubahan tidak tersedia saat nilai dasar 0 atau salah satu periode kosong. Pilihan tahun tidak disimpan sebagai default, agar pilihan tahun tidak membeku sepanjang waktu.

## 6. Rollback

Jika build gagal, **jangan jalankan `up`**. Kembalikan source dari salinan V1.4.6 dan build ulang. Jika aplikasi sudah aktif dan bermasalah, hentikan input sementara, ambil log, pulihkan source V1.4.6 dan rebuild. Tabel preferensi yang baru dibuat tidak mengubah pembacaan lama dan boleh dibiarkan untuk rollback. Jangan pernah menghapus volume database untuk rollback source.

## Batas pengujian paket

Tes Python/SQLite dan syntax TypeScript sudah dijalankan. Build npm/Vite dengan dependensi asli, PostgreSQL Docker, dan browser di LXC **harus dilakukan pada server pengguna**.
