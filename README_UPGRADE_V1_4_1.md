# Upgrade BerauLoad V1.4.0 → V1.4.1 (LXC Proxmox)

**Hanya gunakan patch untuk source V1.4.0 yang sudah terpasang.** Pastikan URL `/api/health` menunjukkan `1.4.0`. Jangan overlay patch pada versi lebih lama.

1. Unggah `BerauLoad_V1_4_1_Update_Patch_From_V1_4_0.zip` ke `/opt` pada LXC.
2. Masuk ke direktori **source aktif** (contoh: `/opt/berauload/BerauLoad_V1_1_1`). Periksa `docker compose ps` dan `curl -fsS http://127.0.0.1:8092/api/health`.
3. Jalankan `./deploy/backup.sh` dan pastikan arsip PostgreSQL serta uploads sudah berhasil dibuat. Simpan backup di lokasi terpisah dari LXC.
4. Backup source aktif sebelum overlay, misalnya `tar -czf /opt/berauload_source_before_141.tar.gz --exclude=.env --exclude=.qa-venv -C "$(pwd)" .` (arsip ini berisi kode, bukan database). Jangan menghapus `.env`.
5. `unzip -o /opt/BerauLoad_V1_4_1_Update_Patch_From_V1_4_0.zip -d .`
6. `docker compose build` — **pastikan semua target berhasil** sebelum lanjut.
7. `docker compose up -d --no-build` lalu `docker compose ps`, `./deploy/smoke-test.sh`, dan periksa versi API `1.4.1`.
8. Uji di browser: Dashboard utama menampilkan default; Edit Layout → Batal; Simpan perubahan; pengaturan status pada 4 daftar; tambah custom Jenis Peralatan; pembuatan Asset dengan jenis baru; rekap H/J tetap sama.

**Rollback kode:** bila build gagal, kembalikan source dari arsip langkah 4, lalu `docker compose build && docker compose up -d --no-build`. Jangan jalankan `docker compose down -v` dan jangan menghapus `pgdata`/`uploads`. Migrasi `equipment_kinds` hanya menambah tabel; rollback source tidak membutuhkan penghapusan tabel baru. Jika sudah ada data kategori baru, fitur kategori tersebut tidak tersedia pada source lama, tetapi tabelnya tetap dipertahankan.

**Catatan:** Script `install.sh` untuk instalasi baru, bukan upgrade. Build Docker/PostgreSQL aktual belum dijalankan di lingkungan pembuatan paket; lakukan staging/smoke test sebelum production.
