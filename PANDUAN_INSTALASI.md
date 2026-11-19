# Panduan Instalasi BerauLoad dari Nol

Untuk orang yang baru pertama kali memasang BerauLoad. Waktu yang dibutuhkan sekitar 20–30 menit. Bila server Anda sudah menjalankan BerauLoad, jangan pakai panduan ini; pakai bagian **Upgrade** di [README.md](README.md).

## 1. Yang harus disiapkan
| Kebutuhan | Keterangan |
|---|---|
| Server | Debian 12 atau Ubuntu 22.04/24.04 (VM, LXC, atau komputer biasa) |
| Sumber daya | Minimal 2 CPU, 4 GB RAM, 20 GB disk. Untuk ribuan gardu, siapkan 8 GB RAM dan disk lebih besar |
| Akses | Pengguna `root` atau `sudo`, dan internet untuk mengunduh Docker dan paket |
| Jaringan | Port 8092 bisa dibuka dari komputer pengguna. Sebaiknya hanya dari jaringan internal atau VPN |

**Bila servernya LXC di Proxmox:** nyalakan dulu opsi *Nesting* (dan *keyctl*) pada container, kalau tidak Docker tidak bisa jalan. Di Proxmox: Container → Options → Features → centang `nesting` dan `keyctl`, lalu restart container.

## 2. Pasang paket dasar dan Docker
Jalankan sebagai root (atau tambahkan `sudo`):

```bash
apt update
apt install -y ca-certificates curl git unzip rsync python3
curl -fsSL https://get.docker.com | sh
docker --version
docker compose version
```
Kedua perintah versi di akhir harus menampilkan nomor versi. Bila `docker compose version` galat, pasang plugin dengan `apt install -y docker-compose-plugin`.

## 3. Ambil source BerauLoad
Pilih salah satu.

**A. Dari GitHub** (repo privat butuh login atau token):
```bash
mkdir -p /opt/berauload
git clone https://github.com/BulusPaijo/berauload.git /opt/berauload/BerauLoad_V1_1_1
cd /opt/berauload/BerauLoad_V1_1_1
```

**B. Dari ZIP** (bila Anda menerima `BerauLoad_V1_6_0_STAGE9D5_Full_Source.zip`):
```bash
mkdir -p /opt/berauload
cd /opt/berauload
unzip /opt/BerauLoad_V1_6_0_STAGE9D5_Full_Source.zip
mv BerauLoad_V1_6_0_STAGE9D5 BerauLoad_V1_1_1
cd BerauLoad_V1_1_1
```
Nama folder `BerauLoad_V1_1_1` dipakai oleh skrip upgrade, jadi sebaiknya jangan diganti.

Pastikan versinya benar: `cat VERSION` harus menampilkan `1.6.0-stage9d5`.

## 4. Jalankan instalasi
```bash
./deploy/install.sh
```
Skrip ini otomatis:
- membuat file `.env` berisi sandi database dan sandi admin acak,
- membangun image dan menjalankan 3 layanan (database, backend, web),
- menampilkan **username `admin` dan sandi awalnya satu kali di layar**.

**Salin sandi admin itu sekarang.** Sandi itu juga tersimpan di file `.env` (hanya bisa dibaca root). Build pertama memakan waktu beberapa menit.

Bila skrip menolak jalan karena izin, jalankan `chmod +x deploy/*.sh` lalu ulangi.

## 5. Periksa bahwa aplikasi hidup
```bash
docker compose ps
curl -fsS http://127.0.0.1:8092/api/health
```
Semua layanan harus berstatus `running` atau `healthy`, dan health harus memuat `"status":"ok"` serta `1.6.0-stage9d5`.

Dari komputer lain, buka `http://IP-SERVER:8092` di browser. Untuk melihat IP server: `hostname -I`.

## 6. Login pertama dan pengaturan awal
1. Login dengan `admin` dan sandi dari langkah 4.
2. **Pengaturan → Struktur Organisasi:** pastikan UP3, ULP, dan KP sesuai kantor Anda. UP3 Berau dan ULP Tanjung Redeb sudah tersedia. Tambahkan ULP atau KP yang belum ada.
3. **Pengaturan → Pengguna:** buat akun untuk petugas. Pilih *jenis akun* (operator, verifikator, manajemen) lalu *akses unit* (ULP atau KP mana yang boleh diisi). Bagikan akun satu per satu, jangan memakai satu akun bersama.
4. **Pengaturan → Branding (opsional):** nama tampilan, logo, dan warna.
5. **Pengukuran Gardu → Master:** tambahkan gardu satu per satu, atau impor dari Excel (tersedia tombol unduh templatenya).
6. **Pengukuran Gardu → Rumus & Kategori:** nilai batas kategori bawaan masih sementara. Sahkan dulu dengan pemilik data sebelum dipakai untuk keputusan.

Panduan pemakaian lengkap ada di [PANDUAN_PENGGUNA.md](PANDUAN_PENGGUNA.md).

## 7. Amankan server
- **Batasi akses.** Jangan buka port 8092 langsung ke internet. Pakai firewall, VPN, atau reverse proxy HTTPS.
- **Bila lewat HTTPS:** ubah `COOKIE_SECURE=true` di `.env`, lalu `docker compose up -d`.
- **Jangan unggah `.env` ke GitHub.** File ini sudah masuk `.gitignore`.
- **Ganti sandi admin** setelah login pertama, dan simpan di pengelola sandi.

## 8. Backup terjadwal
Backup manual:
```bash
cd /opt/berauload/BerauLoad_V1_1_1
./deploy/backup.sh
```
File muncul di folder `backups/` (database dan unggahan, yang lebih dari 30 hari dihapus otomatis).

Agar berjalan setiap malam pukul 01.30, jalankan `crontab -e` lalu tambahkan:
```
30 1 * * * cd /opt/berauload/BerauLoad_V1_1_1 && ./deploy/backup.sh >> /var/log/berauload_backup.log 2>&1
```
Salin folder `backups/` secara berkala ke tempat lain (komputer lain atau NAS). Backup yang hanya ada di server yang sama tidak menolong bila server rusak.

## 9. Perintah sehari-hari
| Keperluan | Perintah (di folder aplikasi) |
|---|---|
| Lihat status | `docker compose ps` |
| Lihat log backend | `docker compose logs --tail 100 backend` |
| Restart | `docker compose restart` |
| Hentikan sementara | `docker compose stop` |
| Jalankan lagi | `docker compose up -d` |

> **Jangan pernah menjalankan `docker compose down -v`.** Opsi `-v` menghapus volume, dan seluruh data pengukuran ikut hilang.

## 10. Masalah yang sering muncul
| Gejala | Penyebab dan cara mengatasi |
|---|---|
| `docker: command not found` | Docker belum terpasang; ulangi langkah 2 |
| Docker gagal jalan di LXC | Aktifkan `nesting` dan `keyctl` pada container (lihat langkah 1), lalu restart |
| `ADMIN_PASSWORD wajib minimal 16 karakter` | Sandi admin di `.env` terlalu pendek. Ubah menjadi minimal 16 karakter, lalu `docker compose up -d` |
| Halaman tidak terbuka dari komputer lain | Cek firewall, dan pastikan port 8092 diizinkan. Cek juga `docker compose ps` |
| Lupa sandi admin | Lihat `ADMIN_PASSWORD` di `.env`. Bila sandinya sudah diganti lewat aplikasi, minta akun admin lain mereset |
| Login terus berulang di HTTP | Pastikan `COOKIE_SECURE=false` bila tidak memakai HTTPS |
| Build gagal karena internet | Ulangi `./deploy/install.sh`. Data tidak berubah karena skrip aman dijalankan ulang |

Bila masalahnya tidak ada di tabel ini, kumpulkan keluaran `docker compose ps` dan `docker compose logs --tail 100 backend` untuk dianalisis.

## 11. Pindah ke versi baru
Setelah terpasang, pembaruan berikutnya memakai ZIP dan skrip upgrade seperti di [README.md](README.md). Tidak perlu memasang ulang.
