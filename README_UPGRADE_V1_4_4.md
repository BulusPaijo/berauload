# Upgrade BerauLoad V1.4.3 → V1.4.4 (LXC Proxmox)

Patch hanya cocok untuk **source V1.4.3**, dengan Docker Compose dan PostgreSQL yang sama. Cek versi `GET /api/health` sebelum memulai. Tentukan maintenance window dan hentikan sementara input operator. Jangan menimpa ZIP Full Source pada instalasi lama.

## 1. Pemeriksaan dan backup

Upload `BerauLoad_V1_4_4_Update_Patch_From_V1_4_3.zip` ke `/opt/` melalui WinSCP.

```bash
cd /opt/berauload/BerauLoad_V1_1_1   # sesuaikan dengan folder aktif
curl -fsS http://127.0.0.1:8092/api/health  # harus version 1.4.3
docker compose ps
./deploy/backup.sh
ls -lah backups | tail -10
```

Pastikan backup PostgreSQL **dan** arsip file import/upload dapat dibaca dan tidak kosong. Salin backup ke media lain di luar LXC. Jika gagal, **STOP**. Simpan snapshot source terpisah:

```bash
cd /opt/berauload
cp -a BerauLoad_V1_1_1 BerauLoad_before_1_4_4_$(date +%Y%m%d_%H%M%S)
```

Sesuaikan nama direktori dengan instalasi aktual. Jangan menyalin direktori besar tanpa ruang disk yang cukup.

## 2. Overlay patch, tes, build

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_4_4_Update_Patch_From_V1_4_3.zip -d .
./deploy/test.sh
docker compose build
```

**Jangan lanjut ke `up`** jika tes atau build gagal. Build frontend memakai npm dengan dependensi asli pada LXC; tidak tervalidasi dari lingkungan pembuat paket.

## 3. Aktivasi dan smoke test

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health   # version 1.4.4
```

## 4. Uji penerimaan di browser

1. Dashboard Builder → Kelola Dashboard: buat dari template dan simpan. Buat, edit lalu gunakan Riwayat Layout untuk pulihkan versi lama.
2. Dashboard pribadi → Bagikan dengan username uji; login sebagai penerima, pastikan hanya melihat; cabut akses, pastikan hilang.
3. Unduh JSON layout; impor sebagai dashboard pribadi baru; jangan sampai mengubah data historis.
4. Laporan → Export Data Excel/CSV: ubah urutan parameter, preview; export CSV dan XLSX lalu buka di Excel. Periksa kolom H dan J, angka 0, jam data kosong, format WITA.
5. Simpan template ekspor pribadi, edit, arsip; untuk admin coba template bersama dan akses pengguna lain.
6. Periksa Dashboard utama, Formula Engine, Historical Calculation, Engineering Rules, Input Harian, dan data final lama tidak berubah.

## 5. Rollback

Jika ada masalah, kumpulkan `docker compose logs --tail=120 backend web` tanpa membagikan `.env`/credential. Pulihkan source lama dari backup lalu build ulang; **jangan** menjalankan `docker compose down -v`. Tabel tambahan V1.4.4 (`export_templates`, `dashboard_shares`, `dashboard_revisions`) dapat dibiarkan dan tidak mengubah tabel pembacaan. Untuk permasalahan data gunakan backup terverifikasi dengan prosedur restore terencana, jangan menghapus database untuk mengulang instalasi.
