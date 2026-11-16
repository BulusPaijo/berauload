# Upgrade BerauLoad V1.5.0 Tahap 4 → Tahap 4.1 — Topology UX Hotfix

Pembaruan additive pada frontend Topologi (search parameter, full-width/focus mode, ubah panjang busbar) dan label versi backend. Tidak ada migrasi schema. **Sumber server harus sudah `1.5.0-stage4` sebelum patch diterapkan.**

## 1. Backup dulu di Debian LXC

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
cd /opt/berauload
tar -czf "BerauLoad_source_before_stage4_1_$(date +%Y%m%d_%H%M%S).tar.gz" --exclude='node_modules' --exclude='.qa-venv' --exclude='backups' BerauLoad_V1_1_1
```

Pastikan backup SQL, uploads dan tar source selesai sebelum menimpa file. Simpan `.env` yang sudah ada; jangan jalankan `install.sh`.

## 2. Patch & validasi

Upload `BerauLoad_V1_5_0_STAGE4_1_Patch_From_STAGE4.zip` ke `/opt/`.

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_5_0_STAGE4_1_Patch_From_STAGE4.zip -d .
./deploy/test.sh
node --test frontend/tests/topology*.test.mjs
docker compose build
```

Jika salah satu gagal, **jangan** jalankan `up` dahulu; lakukan rollback source sesuai bagian 4. Jika build berhasil:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

API seharusnya `version: 1.5.0-stage4.1`. Refresh browser dengan Ctrl+Shift+R.

## 3. Uji browser admin/operator

- Mode Edit: pilih kotak PLTU Lati → Cari parameter → beberapa item; pastikan list bisa discroll, nama terbaca, urutkan pilihan, Simpan/Reload.
- Mode Edit: pilih busbar → ubah panjang dengan input/slider → Simpan/Reload; pastikan **garis yang sudah digambar tidak berpindah otomatis**.
- Mode Lihat dan Edit: uji fullscreen dalam aplikasi melalui Layar Fokus; sidebar disembunyikan. Tampilkan Menu/Esc kembali. Viewer menyediakan Sesuaikan Lebar.
- Periksa hasil pembacaan jam WITA, NULL=`—`, nol tetap `0`, dan hak akses operator tidak memperoleh tombol Edit.
- Periksa Dashboard dan laporan lama tidak berubah, serta tidak ada error konsol.

## 4. Rollback aman tanpa hapus volume

Hentikan deploy baru jika tes/build gagal. Ekstrak kembali tar source yang dibuat pada tahap 1 ke direktori induk (lebih aman diekstrak ke folder sementara lalu overlay, jangan menimpa `.env` sembarangan), kemudian build dan jalankan service kembali:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
docker compose build
docker compose up -d --no-build
./deploy/smoke-test.sh
```

Gunakan tar source cadangan yang benar dari sebelum Tahap 4.1. **Jangan** menghapus volume `db`, menjalankan `docker compose down -v`, atau restore SQL tanpa sebab. Semua diagram tetap di database; patch ini tidak memigrasi data.
