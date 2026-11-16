# Upgrade BerauLoad V1.3.0 → V1.4.0

Paket ini bersifat **kumulatif di atas V1.3.0**. Tidak boleh langsung digunakan untuk V1.2.0/V1.1.x tanpa memasang versi antara. Perubahan database hanya menambah `dashboard_layouts` dan catatan migrasi; tidak mengubah `readings`, `hour_records`, master, formula, historical, atau engineering.

## Pemeriksaan sebelum upgrade

1. Verifikasi API aktif harus menunjukkan `version: 1.3.0`.
2. Simpan backup PostgreSQL **dan** file Excel, lalu verifikasi ukurannya.
3. Simpan snapshot sumber agar perubahan kode bisa di-rollback jika build frontend gagal.
4. Jika ada pengguna aktif, jadwalkan jendela maintenance.

```bash
# Sesuaikan dengan folder proyek yang SESUNGGUHNYA aktif
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
docker compose ps
./deploy/backup.sh
ls -lh backups/berauload_*.gz | tail -4
mkdir -p /opt/berauload_source_backup
umask 077
tar czf /opt/berauload_source_backup/source_before_1_4.tar.gz \
  --exclude='./backups' --exclude='./frontend/node_modules' --exclude='./.qa-venv' .
```

## Terapkan patch

Unggah `BerauLoad_V1_4_0_Update_Patch_From_V1_3_0.zip` ke `/opt/`, lalu jalankan di folder proyek aktif:

```bash
unzip -o /opt/BerauLoad_V1_4_0_Update_Patch_From_V1_3_0.zip -d .
cat VERSION  # 1.4.0
# Build dahulu; berhenti jika ada error npm, TypeScript atau Python.
docker compose build
# Jalankan hanya jika build sukses.
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
docker compose logs --tail=80 backend web
```

**Jangan menjalankan installer ulang. Jangan hapus `.env`, database, `pgdata`, `uploads`, atau volume Docker. Jangan menjalankan `docker compose down -v`.**

## Uji penerimaan browser

- [ ] API `/api/health` menunjukkan `version: 1.4.0`.
- [ ] Berhasil login, data historis lama tetap tersedia, grafik H/J tetap sesuai.
- [ ] Menu **Dashboard Builder** muncul dan membuka default `Monitoring Operasi Berau`.
- [ ] Admin dapat membuat Dashboard Sistem, seluruh pengguna bisa melihat tanpa mengeditnya.
- [ ] Pengguna bisa menduplikasi Dashboard Sistem menjadi Dashboard Pribadi, menambah/mengedit/menghapus panel, drag urutan, ubah lebar, dan menyimpan layout.
- [ ] Dashboard pribadi hanya muncul untuk akun pemiliknya.
- [ ] Default pribadi dapat disimpan; setelah login ulang tetap terbaca.
- [ ] Grafik H/J tetap hanya menampilkan pasangan kolom H dan J valid; data kosong tidak menjadi nol.
- [ ] Panel Historis menampilkan hasil rumus tersimpan sesuai resolusinya; status rule hanya dari rule aktif.
- [ ] Menu **Panduan Pengguna** bisa dibuka, dicari, dan dicetak sebagai PDF browser.
- [ ] Input Beban, Import Excel, Formula Builder, Historical Calculation, Engineering Rules, dan laporan V1.3 tetap berfungsi.
- [ ] `docker compose logs` tidak berisi Traceback atau HTTP 500.

## Rollback

Jika **build gagal**, jangan jalankan `up`; pulihkan source dari `source_before_1_4.tar.gz` dan build ulang. Jika kontainer baru sudah aktif, backup schema V1.4 bersifat additive sehingga backend V1.3 dapat mengabaikan tabel layout baru. Perubahan layout yang dibuat selama V1.4 akan tidak tersedia dari UI V1.3; rollback penuh membutuhkan prosedur restore terpisah yang diuji.

## Catatan keterbatasan

- V1.4.0 tidak mengganti Dashboard Operasi lama; menu **Dashboard Builder** berada terpisah agar alur operator V1.3 tidak berubah.
- Panel tipe Gauge memakai skala visual, bukan ambang batas teknis. Aturan teknis hanya pada rule aktif.
- Belum ada shared dashboard berdasarkan grup, export/import JSON, dan histori versi layout lengkap; itu kandidat V1.4.x mendatang.
- Perhitungan Historis V1.2 masih on-demand, belum menghasilkan snapshot laporan final yang dibekukan per versi.
- Uji backend telah dijalankan menggunakan database QA SQLite. Build npm/Vite dan deployment aktual PostgreSQL/Docker di LXC **harus diverifikasi di server**; jangan menyatakan lolos production sebelum smoke test dan pemeriksaan UI selesai.
