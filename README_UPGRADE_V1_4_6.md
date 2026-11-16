# Upgrade BerauLoad V1.4.5 → V1.4.6

**Wajib dari V1.4.5**, menggunakan `BerauLoad_V1_4_6_Update_Patch_From_V1_4_5.zip`. Jika server masih versi lebih lama, upgrade berurutan atau gunakan jalur migrasi yang sudah diverifikasi. Jangan langsung menimpa server lama dengan paket full source.

## Sebelum upgrade

1. Pastikan API aktif melaporkan `"version":"1.4.5"` melalui `curl -fsS http://127.0.0.1:8092/api/health`.
2. Minta operator menghentikan pencatatan/import sementara dan pastikan tidak ada proses import berjalan.
3. Di folder instalasi aktif jalankan `./deploy/backup.sh`, periksa backup **PostgreSQL dan arsip Excel**. Simpan salinan di lokasi berbeda dan uji restorasi pada staging bila memungkinkan.
4. Cadangkan seluruh folder source termasuk file tersembunyi ke lokasi aman **tanpa mengekspos `.env`**.
5. Jangan menghapus volume Docker, `down -v`, file `.env`, atau menjalankan `install.sh` ulang.

## Instalasi di LXC

Upload ZIP patch ke `/opt/` via WinSCP/SCP, lalu sesuaikan folder aktif:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh

# Buat salinan source di lokasi terpisah sesuai kebijakan kapasitas dan rahasia server.
unzip -o /opt/BerauLoad_V1_4_6_Update_Patch_From_V1_4_5.zip -d .
./deploy/test.sh
# Node 22+ bila tersedia di host:
node --experimental-strip-types --test frontend/tests/*.test.mjs

docker compose build     # Hentikan proses bila build gagal.
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Versi API akhir yang benar adalah `1.4.6`. Jika label browser lama tertinggal, refresh keras `Ctrl+Shift+R`. Frontend sekarang **mengambil versi dari `/api/health`** sehingga tidak perlu mengubah label secara manual pada pembaruan berikutnya.

## Migrasi

- Membuat tabel baru `report_templates` dan marker migrasi `20261114_06_report_templates` secara *additive/idempotent*.
- Tidak menulis ulang tabel pembacaan `hour_records`, `readings`, formula, Engineering Rules, ataupun Dashboard Builder lama.
- Dashboard yang sudah tersimpan tetap terbaca dengan default gaya `classic`, tanpa wajib mengedit ulang panel.
- Konfigurasi gaya yang baru disimpan sebagai properti JSON panel yang tervalidasi; tidak ada skema dashboard yang harus diubah.

## Uji penerimaan di browser

1. Buka **Laporan & Perbandingan**. Pastikan tab **Laporan Standar** masih berfungsi. Masuk **Laporan Kustom**, buat template, tambah Judul/Paragraf/KPI/Grafik/Tabel, pilih parameter dan periode, ubah urutan, lalu pratinjau.
2. Simpan template, ekspor **PDF** dan **Excel**. Periksa file dapat dibuka dan nilainya cocok dengan Analisis Beban. Nilai kosong tidak berubah menjadi 0. CSV kolom bebas tetap di menu **Export Data Excel/CSV**.
3. Buat template Sistem sebagai admin; masuk sebagai manajemen, pastikan dapat melihat tetapi tidak mengubahnya. Template pribadi tidak boleh terlihat oleh pengguna lain.
4. Di **Dashboard Builder → Edit Layout → pensil panel**, uji preset Klasik/Gelap/Lembut, ukuran font judul/angka, warna teks, latar, dan border. Simpan, lalu refresh halaman. Tombol Batal harus mengembalikan gaya tersimpan.
5. Periksa grafik resmi **Daya Mampu (kolom H) vs Beban Sistem (kolom J)**, seluruh Input Beban, Rumus, Perhitungan Historis, Engineering Rules, Dashboard utama, export CSV dan import Excel tetap bekerja seperti versi sebelumnya.
6. Periksa footer, Panduan Pengguna, dan Pengaturan → Informasi Sistem menunjukkan V1.4.6.

## Batas versi

- Report Builder V1.4.6 menggunakan blok berbasis **parameter pengukuran tersimpan** (Input/Computed yang memiliki reading), judul, dan teks. Belum menyediakan laporan dengan blok output Historical Calculation/Engineering Rule langsung atau tampilan drag-and-drop bebas di PDF.
- PDF dan XLSX laporan kustom tersedia setelah template disimpan; **CSV custom dengan urutan kolom tetap memakai Export Data V1.4.4**.
- Periode laporan kustom maksimal 367 hari; resolusi jam maksimal 31 hari. Pratinjau tabel web menampilkan 30 baris; hasil XLSX memuat rentang yang diminta dengan batas periode; tabel PDF dibatasi 120 baris dengan keterangan eksplisit (untuk tabel panjang gunakan Excel).
- Perbandingan dua parameter hanya memakai **jam berpasangan**; slot tanpa pasangan tetap kosong.
- Styling memakai preset dan pilihan aman; pengguna tidak dapat menjalankan CSS/JavaScript bebas dari UI.
- QA offline lulus, **build React/npm asli dan runtime Docker LXC untuk patch ini tetap wajib diverifikasi di server pengguna**.

## Rollback

Jika build gagal, **jangan jalankan `up`**; kembalikan source V1.4.5 dari backup dan build ulang. Jika versi baru terlanjur hidup dan bermasalah, hentikan input, catat log tanpa mengekspor rahasia `.env`, pulihkan source lama, rebuild, dan uji API. Tabel `report_templates` tambahan tidak mengubah data lama; tidak perlu dihapus untuk rollback aplikasi. Jangan memakai `docker compose down -v`.
