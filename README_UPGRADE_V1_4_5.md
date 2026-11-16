# Upgrade BerauLoad V1.4.4 → V1.4.5 (termasuk V1.4.4.1)

Patch **hanya untuk basis source V1.4.4**. Instalasi pada Docker Compose LXC Proxmox yang sudah berjalan. **Jangan menghapus volume dan jangan menjalankan `install.sh` ulang**. Port default tetap **8092**.

## Pra-upgrade

1. Pastikan `curl -fsS http://127.0.0.1:8092/api/health` melaporkan `1.4.4`.
2. Tentukan jeda operasional, minta pengguna menghentikan input, dan pastikan tidak ada proses import aktif.
3. Masuk ke **folder aplikasi yang aktif** (sering `/opt/berauload/BerauLoad_V1_1_1`; jangan menebak folder tanpa `ls`).
4. Jalankan `./deploy/backup.sh`. Pastikan backup PostgreSQL **dan arsip Excel** ada serta bisa dipulihkan. Salin backup ke luar LXC.
5. Cadangkan source dan file `.env` secara aman, jangan bagikan `.env` lewat chat.

## Instalasi

Upload `BerauLoad_V1_4_5_Update_Patch_From_V1_4_4.zip` ke `/opt/`, lalu dari folder aplikasi aktif:

```bash
# Cek versi sebelum patch; harus 1.4.4
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh

# Cadangkan source sebelum patch di luar folder aktif.
# Contoh: cp -a /opt/berauload/BerauLoad_V1_1_1 /opt/berauload/backup_source_v144_$(date +%Y%m%d_%H%M%S)

unzip -o /opt/BerauLoad_V1_4_5_Update_Patch_From_V1_4_4.zip -d .
./deploy/test.sh
node --experimental-strip-types --test frontend/tests/*.test.mjs # opsional: Node 22+ pada host

docker compose build        # BERHENTI jika gagal
# Hanya jika test dan build berhasil:
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health  # version 1.4.5
```

Jika paket `python3-venv` belum tersedia pada Debian, instal paket versi Python yang sesuai (misalnya `python3.13-venv`), kemudian ulangi tes. Jangan menjalankan ulang instalasi aplikasinya.

## Tes penerimaan di browser

1. Buka **Dashboard Builder → Edit Layout**. Tarik ikon pegangan panel untuk menukar posisi; tarik **sudut kanan bawah** untuk mengganti lebar dan tinggi. Ukuran snap 3–12 kolom, tinggi 1–4 tingkat.
2. **Batal** harus membuang perubahan. Coba lagi dan tekan **Simpan Perubahan**, kemudian muat ulang dan pastikan ukuran/urutan tersimpan.
3. Periksa **Dashboard Utama** menampilkan layout yang disimpan. Lebar mengikuti layar, di HP panel ditumpuk vertikal.
4. Bandingkan grafik Daya Mampu (H) dan Beban Sistem (J) dengan versi sebelumnya; data kosong tidak diganti nol.
5. Coba 3–4 parameter berbeda pada satu grafik. Backend sekarang memakai satu permintaan agregasi gabungan. Setelah menyimpan pengukuran baru, muat ulang grafik dan pastikan data berubah (cache lama dibersihkan).
6. Coba ekspor CSV/XLSX untuk periode pendek dan panjang. Urutan dan nilai kolom harus sama seperti versi lama. Ekspor tetap ditulis bertahap ke file temporer, bukan membentuk seluruh workbook di RAM.
7. Login pengguna biasa: dashboard sistem tetap baca-saja. Tes formula historis, Engineering Rules, dan data final masih berfungsi.

## Batas V1.4.5

- Resize sudut tersedia di **desktop**. Pada layar sempit, pilih ukuran melalui dropdown dan urutan melalui tombol panah.
- Drag memindahkan **urutan** dalam grid 12 kolom, bukan koordinat piksel bebas. Posisi panel mengikuti grid responsif sehingga tidak saling menindih.
- Cache agregasi in-memory 45 detik, maksimal 128 entri, dibersihkan pada commit input/import. Backend Compose bawaan menjalankan **1 worker**; bila mengubah konfigurasi menjadi multi-worker, strategi invalidasi cache bersama perlu dirancang ulang. Cache bukan sumber data resmi.
- Ekspor besar tetap memiliki batas V1.4.4 (10 tahun / 120.000 baris / 45 kolom) dan belum memiliki background-job queue.
- Belum ada klaim lolos build React/npm atau runtime Docker di LXC pembuat paket; keduanya wajib diuji di server staging Anda.

## Rollback

Jika build gagal, **jangan** jalankan `up`; perbaiki source atau kembalikan source V1.4.4 dari backup. Jika sudah terlanjur deploy dan menemukan bug, hentikan input, ambil log tanpa `.env`, restore source sebelumnya dan build ulang. Tidak ada perubahan schema pembacaan, sehingga umumnya tidak perlu rollback DB. **Jangan** menjalankan `docker compose down -v`.
