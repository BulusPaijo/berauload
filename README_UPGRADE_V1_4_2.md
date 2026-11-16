# Upgrade BerauLoad V1.4.1 → V1.4.2 (LXC Proxmox)

**Wajib:** pastikan endpoint `/api/health` menampilkan versi `1.4.1`. Patch ini **hanya** untuk source V1.4.1. Periksa juga file kerja lokal bila sebelumnya ada modifikasi manual.

## Pra-upgrade

1. Gunakan WinSCP untuk mengunggah `BerauLoad_V1_4_2_Update_Patch_From_V1_4_1.zip` ke `/opt/` dalam LXC.
2. SSH ke LXC dan masuk ke **direktori proyek yang sedang berjalan** (namanya bisa masih `BerauLoad_V1_1_1`).
3. Konfirmasi versi dan status: `docker compose ps`, lalu `curl -fsS http://127.0.0.1:8092/api/health` (sesuaikan port bila diubah melalui `.env`).
4. Jalankan `./deploy/backup.sh`. Pastikan backup PostgreSQL dan uploads/Excel **berhasil serta tersimpan di tempat terpisah**.
5. Backup source sebelum overlay (jangan sertakan rahasia di lokasi yang tidak aman):

```bash
cd /opt/berauload/BerauLoad_V1_1_1   # GANTI jika path aktif berbeda
mkdir -p /root/berauload-upgrade-backup
# Arsip berikut memuat source dan konfigurasi kecuali .env: simpan privat.
tar -czf /root/berauload-upgrade-backup/source-before-v142.tar.gz \
  --exclude=.env --exclude=.qa-venv --exclude=frontend/node_modules -C "$(pwd)" .
```

## Pasang hanya jika backup sudah diverifikasi

```bash
unzip -o /opt/BerauLoad_V1_4_2_Update_Patch_From_V1_4_1.zip -d .
# Test lokal terisolasi; tidak memakai DB production.
./deploy/test.sh
# Build backend dan frontend dengan dependency asli.
docker compose build
```

**Jika build atau tes gagal: jangan menjalankan `up`.** Simpan log error dan lakukan pemulihan source dari arsip backup.

Jika build dan tes berhasil:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Versi yang diharapkan: `1.4.2`.

## Uji fungsional

1. Login admin → Pengaturan → **Mulai di sini** → **Tab & Kolom Input**.
2. Buat tab `Uji Form`, pindahkan satu parameter input ke tab itu, ubah urutan, klik **Simpan Perubahan**. Buka **Input Beban Harian** dan lihat tab tersebut.
3. Tambah parameter `Input` di Pengaturan → Parameter, pilih **Tab di Input Beban Harian** `Uji Form`; pastikan muncul otomatis pada tabel 24 jam. Isi nilai **0** pada satu jam draft dan simpan. Pastikan nol tersimpan sebagai nol.
4. Sembunyikan parameter uji, lalu lihat bahwa nilai yang tadi disimpan masih ada setelah kolom ditampilkan kembali.
5. Coba **Batal** pada pengaturan tab, lalu reload: tidak boleh ada perubahan yang tersimpan.
6. Periksa input hari Final tetap tidak bisa diedit. Pastikan grafik H (daya mampu) vs J (beban sistem), Formula Engine, Historical Calculation, Engineering Rules, dan Dashboard Builder tetap berjalan.

## Rollback

Jika terjadi error setelah kode di-deploy: pulihkan source dari arsip backup, lalu `docker compose build && docker compose up -d --no-build`. **Jangan** memakai `docker compose down -v`, jangan hapus volume `pgdata` atau `uploads`, dan jangan reset `.env`. Migrasi V1.4.2 hanya membuat tiga tabel baru; tabel lama dan pembacaan tidak diubah. Jika sudah ada konfigurasi tab baru, data itu tetap tersimpan meskipun source kembali V1.4.1, tetapi fitur pengelolaan tab tidak tersedia pada versi lama.

## Batasan

- Tab operator **tidak mengubah mapping Excel lama** (`group_name`, kode dan kolom sumber tetap).
- Belum ada validasi `wajib isi` per parameter agar finalisasi data historis tidak berubah diam-diam.
- Build frontend npm/Vite + Docker/PostgreSQL end-to-end harus diuji pada LXC karena registry npm tidak dapat diakses di lingkungan pembuat source.
