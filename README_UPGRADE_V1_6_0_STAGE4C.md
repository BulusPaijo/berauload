# README_UPGRADE — BerauLoad V1.6.0 Stage 4c

**Kandidat staging (belum lolos `npm run build` akibat DNS eksternal dan belum diverifikasi pada LXC PostgreSQL 16). Jangan langsung upgrade sistem produksi.**

## 1. Backup di server produksi dahulu

1. Simpan arsip source/Compose/.env versi Stage 4b yang berjalan sekarang di luar folder release.
2. Catat nama container dan volume database dengan `docker compose ps` dan `docker volume ls`. Jangan menghapus volume.
3. Buat backup konsisten database, misalnya `docker compose exec -T db pg_dump -U <DB_USER> -d <DB_NAME> -Fc > berauload_before_stage4c.dump` setelah memeriksa nama service, user, dan database dari Compose Anda. Jangan menampilkan password di log.
4. Backup volume uploads sesuai mount produksi dan uji integritas backup `pg_restore --list berauload_before_stage4c.dump`.
5. Pastikan ada rollback copy sumber Stage 4b dan file environment.

## 2. Uji staging sebelum pemasangan

1. Ekstrak ZIP full source Stage 4c ke direktori staging baru, bukan menimpa volume database.
2. Di `frontend/`, jalankan `npm install` lalu `npm run build`; **jika gagal, hentikan rollout**. QA lingkungan build saat rilis ini gagal DNS `EAI_AGAIN`, sehingga uji ini wajib di server dengan akses paket.
3. Di `backend/`, instal dependensi dari requirements yang dibundel lalu jalankan `PYTHONPATH=. pytest -q tests`. Semua tes harus lulus sebelum lanjut.
4. Gunakan PostgreSQL 16 staging dari salinan backup yang terpisah; uji `docker compose build` dan `docker compose up -d` dengan port staging yang tidak bentrok. Jangan menjalankan test otomatis menggunakan database produksi.
5. Periksa `GET /api/health` menunjukkan `1.6.0-stage4c` dan periksa log tidak ada startup error.

## 3. Pemeriksaan aman/read-only sesudah startup staging

Query berikut *hanya SELECT*, sesuaikan koneksi PostgreSQL staging:

```sql
SELECT version FROM schema_migrations ORDER BY version;
SELECT id,code,name,level,parent_id,active,legacy_home FROM org_units ORDER BY id;
SELECT unit_id, COUNT(*) FROM assets GROUP BY unit_id ORDER BY unit_id;
SELECT unit_id, COUNT(*) FROM metrics GROUP BY unit_id ORDER BY unit_id;
SELECT unit_id, COUNT(*) FROM unit_day_states GROUP BY unit_id ORDER BY unit_id;
SELECT scope, unit_id, COUNT(*) FROM dashboard_chart_settings GROUP BY scope,unit_id ORDER BY scope,unit_id;
SELECT scope, unit_id, COUNT(*) FROM standard_report_selections GROUP BY scope,unit_id ORDER BY scope,unit_id;
```

Stage 4c tidak memperkenalkan migrasi DDL atau data baru. Perbaikan preferensi pribadi memakai fallback baca-saja, bukan UPDATE; restart kedua tidak boleh menambah baris atau mengubah `scope`. Bandingkan hasil SELECT dan jumlah Reading/HourRecord dengan snapshot sebelum rollout. Tidak boleh ada relokasi atau kehilangan data ULP Tanjung Redeb.

## 4. Smoke test browser staging (minimal satu akun per peran)

1. Login admin UP3: semua unit aktif terlihat. Pilih ULP Tanjung Redeb, KP lain, lalu UP3. Periksa katalog, banner unit, larangan Input/Import di UP3, serta perubahan unit tidak membawa angka halaman sebelumnya. Uji reload browser dan pilihan unit tersimpan.
2. Login operator ULP: hanya ULP sendiri/KP di bawahnya terlihat; dapat mengisi draft, tidak dapat verify-tree. Login operator KP: ULP induk dan ULP lain **tidak** tampil.
3. Login verifier ULP: pratinjau verify-tree memperlihatkan KP tanpa data *dilewati*; verifikasi ULP tetap berhasil. Uji finalize-tree dan setiap audit. Verifier tidak dapat reopen.
4. Login management UP3 dan management KP: penanda *Hanya lihat*; tidak dapat menulis. Uji endpoint langsung dengan header unit di luar hak dan harapkan 403/404.
5. Admin buat pengguna non-admin tanpa grant (harus 422), lalu dengan grant eksplisit; tambah grant unit kedua dan cabut. Periksa tidak ada grant `legacy_home` yang disisipkan otomatis pada pengguna baru.
6. Admin coba Salin Pengaturan di unit tujuan benar-benar kosong: pratinjau pemetaan dan jumlah, cek peringatan bahwa computed tanpa formula/readings/status tidak tersalin. Atur kembali parameter utama; cek tidak ada data pembacaan palsu.
7. Unduh template import, Excel/PDF, ekspor laporan, dan arsip import pada dua unit yang berbeda: file harus hanya berisi data dari unit aktif.
8. Periksa pasangan `system.load`/`system.capacity`, angka harian, historis dan laporan ULP Tanjung Redeb dibanding Stage 4b. Nilai NULL berbeda dengan angka nol.
9. Restart container staging dua kali; bandingkan COUNT dan hash/daftar baris tabel pref pribadi, audit startup serta laporan migrasi. Tidak boleh muncul transfer baris baru pada start kedua.

## 5. Rollout dan rollback produksi

**Rollout hanya setelah seluruh tes staging dan build frontend lulus serta backup terverifikasi.** Deploy source baru dan `docker compose build && docker compose up -d` menggunakan file env dan volume existing; tunggu healthcheck lalu smoke test. Hindari `docker compose down -v` dan `docker volume rm`.

Jika uji gagal: hentikan container aplikasi, kembalikan source/Compose Stage 4b, jalankan `docker compose up -d --build` **tanpa** menghapus volume. Stage 4c tidak membuat DDL/migrasi baru, tetapi data hasil operasi pengguna setelah upgrade mungkin perlu rekonsiliasi terpisah; jangan restore dump lama begitu saja pada DB yang masih menerima data baru. Bila restore diperlukan, lakukan hanya pada backup konsisten dengan prosedur DBA dan konfirmasi konsekuensi kehilangan perubahan pasca-backup.

## 6. Batas validasi paket ini

QA builder offline berhasil untuk Python/SQLite, tetapi npm install gagal DNS `EAI_AGAIN`, sehingga `npm run build`, browser staging, PostgreSQL 16 dan data produksi **belum** tervalidasi. Anggap ZIP ini kandidat staging, bukan rilis teruji produksi.
