# Upgrade BerauLoad 1.6.0 Stage 7 Hotfix 1 → Stage 8

## Ringkasan dan batas

Stage 8 menambah **branding GLOBAL (satu untuk seluruh UP3/ULP/KP)**. Pengaturan
→ Branding tersedia untuk admin dan tidak membutuhkan rebuild setelah mengganti
teks, warna, logo, atau favicon. Login membaca `GET /api/branding` tanpa sesi.

**JANGAN mengubah pengenal teknis** meskipun nama tampilan diubah: proyek Docker
Compose `berauload`, database/volume, tabel, username database, nama paket,
`/api/health.app = BerauLoad`, cookie sesi, localStorage teknis, format
`berauload-dashboard-v1`, serta `berauload_hourly` pada template Excel **tetap**.
Template Excel historis dan konfigurasi JSON dashboard yang dibuat sebelum
branding diubah tetap menggunakan validasi penanda versi, bukan nama tampilan.

**Status QA:** staging. `npm install` tidak dapat menghubungi `registry.npmjs.org`
(`EAI_AGAIN`) pada lingkungan build pembuat paket; `npm run build` juga gagal
karena React/@types/react belum terpasang. Harus berhasil di staging LXC sebelum
upgrade produksi. Instans PostgreSQL 16 dan UI di browser nyata belum divalidasi.

## 1. Siapkan ZIP dan backup

Unggah `BerauLoad_V1_6_0_STAGE8_Full_Source.zip` ke `/opt/` pada LXC.
Jalankan di staging, jangan langsung pada produksi dengan data asli.

```bash
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
curl -fsS http://127.0.0.1:8092/api/health
# HARUS 1.6.0-stage7-hotfix1 sebelum Stage 8 ini.
./deploy/backup.sh
# Simpan source beserta .env; database/volumes TETAP utuh.
tar -czf "/opt/berauload_before_stage8_$(date +%Y%m%d_%H%M%S).tar.gz" \
  --exclude='./backups' --exclude='./frontend/node_modules' \
  --exclude='./frontend/dist' .
mkdir -p /opt/berauload-stage8-extract
unzip -o /opt/BerauLoad_V1_6_0_STAGE8_Full_Source.zip \
  -d /opt/berauload-stage8-extract
rsync -a \
  --exclude='.env' --exclude='berauload.db' --exclude='backups/' \
  --exclude='uploads/' --exclude='node_modules/' --exclude='dist/' \
  /opt/berauload-stage8-extract/BerauLoad_V1_6_0_STAGE8/ \
  /opt/berauload/BerauLoad_V1_1_1/
cat VERSION
chmod +x deploy/smoke-test.sh
```

**PENTING:** arsip sumber dan cadangan database harus dicek keberadaannya
sebelum menyalin. Jangan pernah menggunakan `docker compose down -v`.

## 2. Jalankan tes dan build secara nyata

Pada Debian tanpa executable `python`, gunakan virtualenv tes Anda sendiri;
contoh `python3 -m venv /opt/berauload-stage8-qa-venv` lalu instal dependensi
backend (`backend/requirements.txt` ditambah `pytest`, `httpx` bila belum ada).

```bash
cd /opt/berauload/BerauLoad_V1_1_1
PYTHONPATH=backend:. /opt/berauload-stage8-qa-venv/bin/python -m pytest -q backend/tests
node --experimental-strip-types --test frontend/tests/*.test.mjs
(cd frontend && npm install && npm run build)
```

Jika salah satu perintah gagal, **hentikan deployment**. Pada Debian LXC
tersedia Docker, `docker compose build` juga menjalankan `npm install` dan
`npm run build` di dalam image Node, tetapi keberhasilan dari build Docker
**tidak menggantikan** kewajiban pengujian terpisah.

## 3. Build Docker, up, dan smoke-test

Jalankan bagian ini hanya setelah langkah 2 lulus pada staging:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
docker compose build
docker compose up -d --no-build
docker compose ps
docker compose exec web nginx -t
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Hasil diharapkan `{"status":"ok","app":"BerauLoad","version":"1.6.0-stage8",...}`.
`app` harus tetap **BerauLoad** karena dipakai oleh skrip dan identitas teknis.

## 4. Migrasi sekali jalan dan pemeriksaan baca-saja

Stage 8 **hanya menambah** tabel `app_branding` dan entri
`schema_migrations` dengan versi `20261117_16_stage8_branding`. Kolom/tabel
lama tidak dihapus atau diubah. Tabel baru memiliki `CHECK (id=1)`. Tanpa
pengaturan branding, tabel boleh kosong dan UI menggunakan nilai bawaan.
Tidak ada backfill/penulisan data operasional. Restart tidak membuat ulang
baris/menggeser data.

```bash
docker compose exec db sh -c \
'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
"SELECT version FROM schema_migrations WHERE version = '\''20261117_16_stage8_branding'\'';"'
docker compose exec db sh -c \
'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
"SELECT id, app_name, logo_version, favicon_version, updated_at FROM app_branding;"'
# Uji POSTGRES dengan SELECT saja sebelum/sesudah restart;
# tidak boleh ada penambahan baris tanpa tindakan admin.
```

## 5. Uji browser satu akun admin dan satu non-admin

1. Buka URL staging/login tanpa sesi. Nama dan ikon bawaan BerauLoad muncul,
   login tetap tampil meski endpoint branding sementara tidak tersedia.
2. Admin → Pengaturan → Branding. Coba ganti nama, tagline, warna utama gelap,
   warna aksen, deskripsi, teks login/footer. Simpan. Periksa login di tab baru,
   sidebar, judul tab browser, favicon, dan Informasi Sistem.
3. Unggah PNG/JPEG/WebP logo (maksimal 512 KB, dimensi maksimal 1024×1024),
   atau PNG/ICO/WebP favicon (128 KB, 256×256). Gambar diproses ulang menjadi
   PNG; metadata dibuang. **SVG unggahan dilarang** (berisiko skrip), namun
   favicon SVG bawaan proyek aman.
4. Coba unggah berkas HTML/SVG atau warna utama putih: harus ditolak.
   Coba Hapus logo/favicon dan **Kembalikan semua ke bawaan** (konfirmasi).
5. Pastikan pengguna operator, verifier, management, KP tidak dapat mengubah
   branding, meskipun mengirim URL API langsung; GET publik tetap boleh.
6. Bandingkan data historis/angka sebelum dan sesudah, buat PDF/XLSX, serta
   impor kembali template Excel dan JSON dashboard lama. Nama unduhan/sheet
   menampilkan branding, **struktur dan data sumber tidak berubah**.
7. Menyimpan branding ketika halaman Input Beban Harian memiliki isian
   belum tersimpan harus tidak menghapus isian/backup lokal Stage 7.

Pengguna lain melihat branding terbaru setelah **memuat ulang** halaman;
tidak ada polling/WebSocket baru. Browser dapat men-cache favicon, namun URL
mengandung versi berbeda setelah unggahan/hapus.

## 6. Rollback tanpa menghapus volume

Sebelum rollback, simpan lagi backup database dan uploads yang saat itu ada.
Hentikan deployment bila skema/data perlu dikembalikan ke kondisi lama;
jangan pernah menjalankan `down -v`, `DROP`, atau menghapus volume.

```bash
cd /opt/berauload/BerauLoad_V1_1_1
./deploy/backup.sh
# Pulihkan backup SOURCE yang Anda buat pada langkah 1 (bukan database),
# misalnya: tar -xzf /opt/berauload_before_stage8_YYYYMMDD_HHMMSS.tar.gz -C .
# Pastikan memilih arsip yang benar, lalu:
docker compose build
docker compose up -d --no-build
docker compose ps
curl -fsS http://127.0.0.1:8092/api/health
```

Tabel `app_branding` yang bersifat aditif dan file `uploads/branding/*.png`
akan tetap berada di volume; Stage 7 mengabaikannya. Jangan hapus tabel/volume
saat rollback. Setelah memperbaiki kendala, Stage 8 dapat dipasang kembali.

## Keterbatasan validasi pembuat paket

Pengujian sintetik SQLite/Node dilakukan dan dicatat di QA_STATUS_STAGE8.md.
Tidak ada pengujian PostgreSQL 16 di LXC, browser (termasuk favicon cache,
aksesibilitas warna aktual, render logo), Cloudflare Tunnel, atau penggunaan
logo korporat resmi. Pemilik proyek wajib memastikan hak pakai logo.
`pillow==12.3.0` dipin sesuai paket Pillow yang diperiksa di Python QA;
versi yang benar-benar terpasang di Docker produksi harus diperiksa kembali
sesudah build.
