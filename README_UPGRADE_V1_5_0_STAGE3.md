# Upgrade BerauLoad V1.5.0 Tahap 2 → Tahap 3 (Visual Editor)

**Paket ini hanya untuk API `1.5.0-stage2` yang telah berjalan baik.** Tahap 3 memperluas frontend dan nomor versi API. **Tidak ada migrasi database baru**. Patch tidak menghapus `.env`, tabel pembacaan, formula, atau revisi topologi.

## 1. Periksa versi dan backup

Jalankan pada LXC dari folder aktif yang Anda pakai selama ini (contoh):

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
```

Pastikan versi `1.5.0-stage2`, `backups/...sql.gz` dan `...uploads.tar.gz` sukses. Cadangkan source terpisah dari direktori yang akan ditimpa:

```bash
mkdir -p /opt/berauload/source-backups
stamp=$(date +%Y%m%d_%H%M%S)
tar -czf "/opt/berauload/source-backups/source_pre_stage3_${stamp}.tar.gz" \
  --exclude='.qa-venv' --exclude='node_modules' --exclude='backups' \
  --exclude='.git' --exclude='.env' -C /opt/berauload BerauLoad_V1_1_1
```

Kunci/session/password `.env` tetap di server dan jangan dibagikan. Simpan backup konfigurasinya secara aman bila diperlukan.

## 2. Patch dan tes SEBELUM mengaktifkan

Upload `BerauLoad_V1_5_0_STAGE3_Patch_From_STAGE2.zip` ke `/opt/` menggunakan WinSCP.

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_5_0_STAGE3_Patch_From_STAGE2.zip -d .
./deploy/test.sh
node --test frontend/tests/topologyViewer.test.mjs frontend/tests/topologyEditor.test.mjs
docker compose build
```

**Jangan lanjut ke `up` jika satu tes atau build gagal.** Build Docker harus menampilkan sukses untuk backend DAN web, termasuk `npm run build` (React/TypeScript/Vite). QA offline tahap ini belum bisa memverifikasi npm asli, sehingga build di LXC sangat penting.

## 3. Aktifkan hanya jika build lulus

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

API diharapkan mengembalikan `version: 1.5.0-stage3`. Pastikan semua container sehat lalu **Ctrl+Shift+R** di browser.

## 4. Uji penerimaan di browser

- Login sebagai admin, buka Monitoring → Topologi, dan buat diagram kosong melalui **Diagram Baru**.
- Tekan **Edit Diagram**, tambah Kotak Parameter, pilih hingga enam parameter, atur urutannya, dan seret kotak. Periksa snap-grid 10 px dan lebar.
- Tambah simbol dengan **Buat draf dari daftar peralatan**: hanya simbol, **tidak boleh ada garis sambungan yang dibuat otomatis**.
- Coba Undo/Redo, Reset dan Batal. Setelah Batal, muat ulang: perubahan draft tidak boleh tersimpan.
- Edit lagi, Simpan, refresh: posisi dan isi parameter harus tetap. Periksa Riwayat Revisi dan pemulihan sebagai versi baru.
- Coba mengubah diagram dari dua tab admin: penyimpanan versi lama harus menghasilkan HTTP 409 dengan pesan muat ulang.
- Login sebagai operator/manajemen: mode Edit dan tombol Diagram Baru **tidak muncul**, sedangkan Mode Lihat tetap berfungsi.
- Cocokkan nilai per jam dengan Input/Data Historis. NULL harus `—`, 0 harus 0. Tidak ada kendali pemutus.
- Periksa regresi Dashboard, Formula Engine, Engineering Rules, import Excel, dan Laporan.

## 5. Rollback aman

Jika build gagal, **jangan aktifkan image baru**. Pulihkan source Stage 2 dari backup yang dibuat sebelum unzip (serta `.env` tetap berada di lokasi lama), lalu build ulang jika diperlukan. Jika sudah mengaktifkan dan terdapat masalah, pulihkan source Tahap 2, jalankan `docker compose build && docker compose up -d --no-build`, lalu smoke test. Tidak ada tabel baru di Tahap 3, sehingga rollback source tidak membutuhkan perubahan database. Jangan jalankan `docker compose down -v`, `install.sh`, atau hapus volume PostgreSQL.

Tahap 3 adalah kandidat staging hingga tes Docker dan browser LXC lolos. Kode pengukuran dan Formula Engine tidak disentuh.
