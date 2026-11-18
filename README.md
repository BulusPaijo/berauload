## Stage 9c-fix — Koreksi filter PostgreSQL dan build TypeScript (17 November 2026)

Patch kecil kumulatif di atas Stage 9c, dapat di-upgrade langsung dari Stage 9b. Filter angka sekarang berkorelasi pada ID pengukuran yang dipilih, query temuan dapat memakai beberapa kode, input salah menghasilkan HTTP 422, dan deklarasi helper React diselaraskan. **Kandidat staging**: build frontend sungguhan dan eksekusi PostgreSQL 16 di LXC masih perlu dibuktikan. Lihat `README_UPGRADE_V1_6_0_STAGE9C_FIX.md` dan `QA_STATUS_STAGE9C_FIX.md`.

## Stage 9c — Analisa Gardu dan Hotfix Hitung Ulang (17 November 2026)

**Kandidat staging** di atas Stage 9b: benturan dua proses hitung ulang
ditangani dengan kunci transaksi PostgreSQL dan SKIP LOCKED; draf rumus bersiklus
ditolak; jurusan yang tidak ada bukan sumber kosong; preview dampak menampilkan
contoh tanpa menulis. Halaman **Pengukuran Gardu → Analisa** menyediakan mode
terakhir/periode/semua, filter SQL kolom hitung dan aturan admin, sortir NULL di
akhir, tabel responsif, ekspor CSV/XLSX + keterangan versi, serta tampilan pribadi
atau bersama. Definisi dan data ukur Stage 9b/9a tidak diubah.

**Jangan upgrade production sebelum validasi PostgreSQL 16, Docker build, browser,
dan pengukuran kinerja LXC.** Lihat `README_UPGRADE_V1_6_0_STAGE9C.md` serta
`QA_STATUS_STAGE9C.md`.

## Stage 9b — Rumus & Kategori Pengukuran Gardu (17 November 2026)

Kandidat staging di atas **Stage 9a-fix**. Admin global dapat menyusun **kolom
hitung, kategori, temuan, konstanta**, dan ambang *belum diukur* yang berlaku di
seluruh unit melalui **Pengukuran Gardu → Rumus & Kategori**. Ekspresi memakai
parser AST aman yang sama dengan rumus beban harian, dengan ekstensi yang hanya
aktif dalam konteks gardu. Hasil turunan disimpan per kunjungan sebagai tabel
relasional berversi; data ukur verified tetap tidak dapat diubah. Revisi definisi
menaikkan versi dan dapat dihitung ulang secara bertahap dan dilanjutkan.

**Penting:** definisi awal merupakan konfigurasi *sementara* yang harus disetujui
pemilik sebelum dipakai untuk keputusan teknis. Dibutuhkan validasi PostgreSQL 16,
NPM build, dan browser di LXC pengguna. Panduan: `README_UPGRADE_V1_6_0_STAGE9B.md`,
`QA_STATUS_STAGE9B.md`. Tahap 9c (tabel analisa) dan 9d (peta/grafik) **tidak**
masuk paket ini.

## Stage 9a — Pengukuran Gardu (17 November 2026)

Pengukuran beban gardu distribusi kini dicatat **per kunjungan** (gardu/tanggal/sesi), terpisah sepenuhnya dari pembacaan per jam. Modul `substations` memiliki master gardu+penyulang, definisi parameter global, sesi/flag, snapshot trafo dan penyulang, penyimpanan draft/verified ber-revision, Excel/CSV preview-first, aksi massal, serta kisi input dan form ponsel. Migrasi hanya tabel baru, tidak menyentuh `HourRecord`/`Reading`. Stage 9b (rumus/kategori/analisis) belum diimplementasikan. **Kandidat staging: build frontend dan PostgreSQL/browser LXC wajib divalidasi**. Baca `README_UPGRADE_V1_6_0_STAGE9A.md` dan `QA_STATUS_STAGE9A.md`.

### Stage 8 — Branding global yang dapat diatur

Versi terbaru `1.6.0-stage8`: Pengaturan → Branding (admin) mengubah nama tampilan, logo, favicon, warna, teks login, header/footer laporan dan unduhan tanpa rebuild setelah perubahan setting. Identitas teknis BerauLoad, format template Excel/JSON, kunci localStorage/cookie, database serta Compose **tetap**. Lihat `README_UPGRADE_V1_6_0_STAGE8.md` dan `QA_STATUS_STAGE8.md` sebelum pemasangan staging/produksi.

## BerauLoad 1.6.0-stage7-hotfix1 — Hotfix alat uji beban dan Nginx (16 November 2026)

Hotfix terbatas `deploy/loadtest`: runner mendukung dua jalur, skenario pembaca memakai endpoint sebenarnya, fixture memberi role system.load/capacity serta data/diagram sintetis, dan laporan menegakkan kriteria LULUS/GAGAL. `frontend/nginx.conf` diperbaiki dengan tanda kutip pada regex cache aset; `deploy/smoke-test.sh` executable. Perubahan backend/UI hanya **metadata versi**, tanpa migrasi, logika kelistrikan, atau izin. PostgreSQL 16/20+60 pengguna belum diuji di lingkungan build; `npm install` gagal DNS `EAI_AGAIN`, `npm run build` belum lulus. Lihat `README_UPGRADE_V1_6_0_STAGE7_HOTFIX1.md`, `deploy/loadtest/README.md`, `QA_STATUS_STAGE7_HOTFIX1.md`.

## V1.6.0 Stage 7 — Keandalan Pengisian dan Banyak Pengguna (16 November 2026)

**Kandidat staging**. Simpan manual jam kini hanya mengubah kode yang dikirim,
memakai optimistic baseline opsional dan (di PostgreSQL) advisory transaction lock
berdasarkan (unit,tanggal,jam). Nilai sama -> unchanged tanpa audit/recalc;
konflik kode yang sama -> 409, tanpa partial write. Autosave per jam 3 detik,
blur, dan antrean per jam; cadangan lokal per user/unit/tanggal, pemulihan harus
disetujui; 401 login ulang akun yang sama; 409 resolusi per parameter. Sesi
bergeser paling sering setiap lima menit, maksimum 24 jam sejak login.

Satu worker tetap wajib karena cache/setup lintas proses belum divalidasi.
Kolam DB configurable, Nginx gzip/cache/rate limit dan skrip uji beban yang
menolak produksi sudah ditambahkan. Satu migrasi aditif session/login.
**Frontend build dan PostgreSQL/browser/load kapasitas belum dianggap lulus**
hingga diverifikasi. Panduan: `README_UPGRADE_V1_6_0_STAGE7.md`; uji beban:
`deploy/loadtest/README.md`; hasil tes aktual di `QA_STATUS.md`.

## V1.6.0 Stage 6 — Pemantauan Lintas Unit (16 November 2026)

**Kandidat staging, tidak ada migrasi skema atau data.** Monitoring → Kelengkapan Unit menyediakan matriks baca-saja maksimal 62 hari bagi ULP/KP yang dapat dibaca, status D/V/F, dasar `system.load` atau `any_input`, jam WITA yang telah dimulai, drilldown ke Input Harian (mode Hanya lihat untuk management), dan ekspor XLSX aman. Hari sekarang termasuk jam yang sedang berjalan; hari depan berharapan 0. `GET /api/org-units/{id}/completeness` terpisah dari `/api/formulas/completeness`. SQL melakukan satu agregasi GROUP BY untuk seluruh unit/hari, tidak menarik pembacaan per sel.

Editor Topologi admin dapat menambahkan tautan simbol ke diagram unit bawah, tersimpan bersama layout JSON/revisi tanpa perubahan jaringan listrik. Viewer dapat menelusuri tanggal/jam sama dan kembali lewat breadcrumb; unit yang tidak berhak baca tidak ditampilkan. Restore dengan target yang diarsipkan ditolak sambil menyebut ID simbol. UP3 menampilkan daftar bertingkat diagram anak, tanpa membuat diagram otomatis.

**Build frontend di host pengembangan belum berhasil karena npm registry DNS `EAI_AGAIN`; paket belum dinyatakan siap produksi.** Panduan pemasangan di `README_UPGRADE_V1_6_0_STAGE6.md`, QA di `QA_STATUS.md`.

## V1.6.0 Stage 5 Hotfix 1 — Template Import dan Rekap Lintas Unit (16 November 2026)

`template_import/service.py::write()` kini memanggil `recalculate()` **sekali per jam** setelah semua pembacaan yang benar-benar baru (input unggahan dan computed lokal) dicatat, dalam transaksi commit import yang sama. Rujukan KP → ULP → UP3 dihitung otomatis dari operand eksplisit, tetap menghormati NULL, angka 0, dan status verified/final ULP. Jika hitung ulang gagal, `template_import/router.py::commit()` yang sudah ada membatalkan seluruh transaksi dan menghapus arsip tanpa batch. Tidak ada migrasi skema atau fitur lain. Lihat `README_UPGRADE_V1_6_0_STAGE5_HOTFIX1.md` dan `QA_STATUS.md`. **Build frontend lokal belum lulus karena npm registry DNS EAI_AGAIN; validasi staging wajib.**

### Stage 5 — Data Unit Bawah (2026-11-16)

UP3/ULP dapat memakai rujukan parameter anak secara baca-saja di formula, dashboard, topologi, historical, engineering rules, report, dan export. Parameter dipilih per unit, operand rekap **wajib eksplisit** (tanpa auto sum), keterisian ketat (NULL ≠ 0), dengan recalc berantai pada transaksi penyimpanan pembacaan. Status sumber dan penanda perubahan pada hari ULP terkunci dapat dilihat verifier/admin. UP3 tetap computed-only; tidak ada status hari UP3. Upgrade dan langkah rollback: `README_UPGRADE_V1_6_0_STAGE5.md`. Status QA: kandidat staging hingga npm/Vite, PostgreSQL, browser dan angka produksi selesai diverifikasi.

> **Stage 4c UI Hotfix 1 — Pengaturan > Pengguna (16 November 2026).** Form pengguna sekarang memisahkan Jenis akun dan Akses unit; daftar menampilkan akses unit dengan endpoint yang sudah ada. Perubahan izin/backend hanya pembaruan string versi. 43 tes Node lulus, tetapi `npm install` gagal `EAI_AGAIN`; build frontend belum lulus dan pengujian browser/PostgreSQL belum dilakukan. Lihat `QA_STATUS.md` serta `README_UPGRADE_V1_6_0_STAGE4C_UI_HOTFIX.md`.

> **Source kandidat staging aktif: BerauLoad V1.6.0 Stage 4c.** Antarmuka pemilih unit, manajemen akses pengguna, pratinjau aksi massal, dan fallback preferensi pribadi sudah dikembangkan. **BELUM LULUS BUILD FRONTEND** karena npm registry tidak dapat diakses (`EAI_AGAIN`); belum diuji dalam browser dan PostgreSQL 16 LXC produksi. Jangan upgrade produksi langsung. Lihat `README_UPGRADE_V1_6_0_STAGE4C.md` dan `QA_STATUS.md`.

> **Versi aktif source: V1.6.0 Stage 4b** — penyimpanan konfigurasi per unit dan Salin Pengaturan admin. Tahap 4c belum dibuat. Lihat `README_UPGRADE_V1_6_0_STAGE4B.md` dan `QA_STATUS.md`.

# BerauLoad V1.6.0 Tahap 4a — Operasional per Unit (2026-11-15)

**Kandidat staging. Tahap 4a saja; 4b dan 4c belum diimplementasikan.** Aplikasi BerauLoad sudah digunakan oleh pengguna di LXC dengan data produksi, tetapi patch ini belum diuji pada LXC/PostgreSQL 16 tersebut.

- Backend memakai header opsional `X-Unit-Id` untuk memilih unit. Tanpa header, admin global menggunakan ULP `legacy_home` (ULP Tanjung Redeb); pengguna non-admin menggunakan unit aktif tertinggi yang tercantum dalam hak akses. ULP mewariskan hak baca dan hak input/verifikasi ke KP di bawahnya; akses unit lain ditolak; KP tidak membaca induk. Admin global dapat mengoperasikan ULP/KP mana pun, tetapi UP3 sendiri tidak memiliki pembacaan/input.
- Seluruh endpoint pembacaan/analitik/dashboard/monitoring/laporan, catatan jam, import, dan katalog diberi filter `Metric.unit_id`. Parameter eksplisit unit lain ditolak 404. `HourRecord` tetap slot global `day + hour` WITA; sumber data tetap `Reading` dan tidak ditulis ulang oleh migrasi ini.
- `unit_day_states` kini sumber status per unit. Pada `legacy_home`, perubahan verify/finalize/reopen dicerminkan dalam transaksi yang sama ke `day_states` lama; perubahan status tidak menimpa pembacaan. Tambahan API `POST /api/days/{day}/verify-tree` dan `/finalize-tree` memproses ULP beserta KP aktif dalam satu transaksi; gagal satu unit membatalkan seluruh perubahan. Reopen hanya admin global.
- Aksi penulisan data menyertakan unit, pengguna dan peran efektif di audit. Konfigurasi hanya admin global. Formulasi `catalog.calculate()` dan import laporan lama tetap **hanya** berlaku pada `legacy_home`; unit lain menggunakan Formula Engine dan Template Import.
- Untuk mempertahankan keamanan sebelum 4b, konfigurasi legacy Topologi, Dashboard Builder, Perhitungan Historis, Form Input, Engineering Rules dan Laporan Kustom dibatasi pada lingkup `legacy_home` (atau UP3 yang berhak baca seluruh bawahan); API konfigurasi per unit akan diselesaikan di Tahap 4b. Tidak ada penyalinan konfigurasi baru pada 4a.
- Pemilih unit di UI, penanda hanya-lihat, dan formulir memilih unit saat membuat user baru **belum tersedia**: semuanya bagian 4c. Untuk sementara uji unit lain memakai header `X-Unit-Id` melalui klien API. Jangan mengklaim semua halaman unit baru sudah mendukung konfigurasi atau UI pada tahap ini.

Dokumentasi teknis: `ARSITEKTUR.md`; QA: `QA_STATUS.md`; upgrade dan rollback: `README_UPGRADE_V1_6_0_STAGE4A.md`. Rilis hanya setelah `npm run build`, Docker, pengujian Postgres dan audit data produksi berhasil.

---

# BerauLoad V1.6.0 Tahap 3 — Parameter Utama per Unit (2026-11-15)

**Kandidat staging, belum diverifikasi di PostgreSQL 16/Docker/browser LXC pengguna.** Tahap ini menambahkan resolver role semantik terpusat: `system.capacity` dan `system.load` pada unit `legacy_home` (ULP Tanjung Redeb). Kode parameter bawaan `daya_pasok_pembangkit_kw` (rekap H) dan `beban_sistem_kw` (rekap J) tetap ada dan tetap dipakai selama kedua `role_key` masih menunjuk ke sana. Tidak ada migrasi data dan tidak ada penulisan ulang pengukuran, formula, dashboard, atau revisi tersimpan.

- **Pengaturan (admin) → Parameter utama unit**: pilih parameter aktif untuk beban sistem dan daya mampu atau kosongkan peran; perubahan dicatat di audit. Peran disimpan pada `metrics.role_key` yang sudah tersedia sejak Stage 1; unik per unit. Tidak ada pemilih unit operasional sampai Tahap 4.
- `GET /api/catalog` menambah `roles` (`role_key → metric.code`); endpoint bawaan Dashboard, Analytics/Compare, kapasitas-vs-beban, laporan dan preset baru mengikuti peran. Jika role hilang, endpoint return HTTP 200, `configured:false`, data tidak diada-adakan. Seluruh data WITA historis dan API eksplisit tetap dipertahankan.
- Grafik H/J tetap memakai agregasi berpasangan dan larangan stacked series **menurut pasangan role pada unit sama**, bukan string kode. Default sistem baru mengikuti role; konfigurasi/revisi pengguna yang sudah disimpan tidak dipindah atau diedit diam-diam.
- `GET /api/metrics/{id}/usage` memberikan dependensi parameter. Penonaktifan parameter yang dipakai memerlukan konfirmasi dan mencatat audit. Perintah “Terapkan ke Peralatan Sejenis” pada editor Topologi mencocokkan `role_key` lebih dahulu, kemudian nama+satuan jika tidak punya role.
- Import Laporan Lama (`importer.py`) dan Template Import Tahap 2, katalog seed, data jam, formula penghitungan lama, serta versi migrasi terdahulu tidak diganti.
- Rincian: `README_UPGRADE_V1_6_0_STAGE3.md`, `ARSITEKTUR.md`, `PANDUAN_PENGGUNA.md`, `QA_STATUS.md`. **Jangan instal di LXC data nyata sebelum backup, tes, dan Docker build lulus.**

---

# BerauLoad V1.6.0 Tahap 2 — Import Template (2026-11-15)

**Kandidat staging, belum dipasang/diuji pada PostgreSQL 16 LXC pengguna.** Tambahan jalur **Template BerauLoad** pada menu Import Excel, tanpa mengubah jalur **Laporan lama** (`importer.py`, `/api/imports/*`). Template Excel dibuat dari parameter input aktif yang tampil pada Form Input untuk unit `legacy_home` (ULP Tanjung Redeb), data per jam WITA, rentang 1–92 hari.

- API khusus `GET /api/template-import/template`, `POST /api/template-import/preview`, `POST /api/template-import/commit`, ditambah config/history; sumber unit eksplisit di seluruh helper. Belum ada unit selector atau filter operasional multi-unit.
- Bawaan `fill_empty`, opsional `new_hours`; **tidak ada mode overwrite**. Hari non-draft dilewati; reading existing (termasuk computed) tidak diubah; nol tetap nol, kosong dilewati. Computed baru melalui kalkulator yang sama dengan entri manual, hanya bila belum tersedia.
- Periksa XLSX tanpa menjalankan rumus, tolak formula di mana pun, kode/sel/metadata invalid dengan alamat sel. Konfirmasi memakai token+SHA256+arsip dan satu transaksi DB; file identik untuk unit yang sama ditolak 409.
- Migrasi `import_batches.kind` additive/idempotent: batch lama `legacy_excel`, batch baru `template`. Tidak mengubah readings/hour_records/day_states historis saat upgrade.
- Lihat `README_UPGRADE_V1_6_0_STAGE2.md`, `ARSITEKTUR.md`, `PANDUAN_PENGGUNA.md`, dan `QA_STATUS.md` untuk batas validasi nyata.

---

# BerauLoad V1.6.0 Tahap 1.2 — Migrasi Data Sekali Jalan

**Kandidat staging.** Perbaikan hanya pada urutan migrasi `org_units`; **tidak ada skema atau aturan bisnis baru**. Jika versi migrasi Stage 1 / Stage 1.1 telah tercatat di `schema_migrations`, startup berikutnya tidak lagi menyalin `unit_day_states`/`user_unit_access` atau memindahkan data ke ULP Tanjung Redeb. Perbaikan `unit_id IS NULL` pada asset/metric/import batch tetap diperbolehkan ketika ada data tidak berunit akibat code-only rollback.

- Parameter computed yang sah di UP3, akses non-admin di UP3, kombinasi role UP3/ULP yang berbeda, serta akses eksklusif ULP lain dipertahankan saat restart.
- Database Stage 4.2/Stage 1 masih menjalankan backfill awal tepat sekali sampai Stage 1.1 tercatat, sedangkan database Stage 1.1 yang telah selesai **tidak dimigrasikan ulang**.
- Tidak ada filter per unit, perubahan izin operasional, pemilih unit, atau pengubahan `readings`, `hour_records`, `day_states`.
- Tes lama `test_api_hierarchy_csrf_access_and_audit` diperbarui hanya pada asersi yang sudah tidak sesuai dengan seed ULP Tanjung Redeb dan penempatan akses non-admin. Semua pengujian wajib dijalankan tanpa skip.
- Lihat `README_UPGRADE_V1_6_0_STAGE1_2.md` dan `QA_STATUS.md`. Belum ada konfirmasi instalasi Stage 1.2 di LXC pengguna.

---

# BerauLoad V1.6.0 Tahap 1.1 — Legacy Home ULP Tanjung Redeb

**Status: kandidat staging; bukan perbaikan pembatasan multi-unit.** Seluruh pengukuran historis yang sebelumnya tertaut ke UP3 sekarang ditautkan ke `ulp_tanjung_redeb` (anak langsung UP3). Struktur dibangun melalui migrasi additive dan idempotent; nilai di `readings`, `hour_records`, dan `day_states` **tidak diubah**.

- Seed unit hanya UP3 Berau dan ULP Tanjung Redeb. KP lain tidak ditambah otomatis.
- `legacy_home` unik, hanya `ulp_tanjung_redeb = TRUE`. Kode permanen.
- Asset, metric (termasuk computed existing), import batch, mirror status harian bermilik ULP Tanjung Redeb; admin akses UP3, non-admin akses ULP dengan role global yang sama.
- Semua endpoint operasional tetap menggunakan `User.role` global, tanpa selector/filter unit. Pembacaan `day_states` tetap sumber resmi. Formula/Historical/Engineering/Topologi tidak diubah.
- **Regresi Stage 1 lama:** satu tes `test_api_hierarchy_csrf_access_and_audit` masih mengharapkan UP3 tanpa ULP dan secara logis tidak kompatibel dengan seed wajib ULP. File tes lama dibiarkan tidak berubah; lihat `QA_STATUS.md`.
- Lihat `README_UPGRADE_V1_6_0_STAGE1_1.md` sebelum upgrade LXC. Pengguna telah melaporkan BerauLoad versi sebelumnya berjalan di LXC; belum ada validasi nyata atas patch ini.

---

# BerauLoad V1.6.0 Tahap 1 — Fondasi Multi-Unit

**Kandidat staging** yang meneruskan semua fitur V1.5.0 Tahap 4.2 tanpa mengubah hasil/izin lama.

## Struktur organisasi

- Pengaturan (admin) → **Struktur Organisasi**: satu UP3 `up3_berau` / “UP3 Berau” (nama bisa diedit), ULP anak UP3, KP anak ULP; tidak membuat seed ULP/KP.
- Kode unit, jenis, peralatan dan parameter tetap stabil; KP/ULP bisa dinonaktifkan dengan syarat; tidak ada hapus permanen.
- Data legacy `assets`, `metrics`, `import_batches` ditautkan ke UP3. Semua pengguna lama mendapat akses role globalnya pada UP3. `role_key` disiapkan untuk identifikasi fungsi semantik tetapi **belum mengubah pengukuran**.
- `day_states` tetap sumber baca resmi. `unit_day_states` hanya salinan UP3 saat upgrade dan diperbarui dalam satu transaksi pada verify/finalize/reopen.
- Fungsi murni pewarisan baca UP3→ULP→KP dan tulis lokal sudah diuji tetapi **belum diterapkan** pada API operasional. Tidak ada filter unit, tidak ada menu pemilih unit, dan seluruh halaman/role lama tetap seperti Stage 4.2.
- Tambah modul `backend/app/modules/org_units` dan `frontend/src/features/org-units`; lihat `ARSITEKTUR.md` serta `README_UPGRADE_V1_6_0_STAGE1.md`.
- **Perhatikan:** UP3 di-seed otomatis satu kali jika tabel organisasi kosong; **tidak ada ULP atau KP bawaan**.


---

# BerauLoad V1.5.0 Tahap 4.2 — Compact Workspace & Visual Groups

> Kandidat staging. Mode Lihat dan Mode Edit (admin), delapan simbol, koneksi manual dan Group Area visual tersedia. Baseline kumulatif Tahap 1 + V1.4.6.1.

Aplikasi web untuk pengukuran kelistrikan per jam, rekap historis, Formula Engine, Engineering Rules, Dashboard Builder, dan laporan. **Source ini kumulatif:** V1.4.6.1, Backend Topologi Tahap 1, Viewer Tahap 2, Visual Editor Tahap 3, dan Diagram Builder Tahap 4.

## Teknologi

- Backend: Python 3.12, FastAPI, SQLAlchemy, ReportLab, openpyxl.
- Frontend: React 19, TypeScript, Vite, Recharts.
- Database: PostgreSQL 16 pada Docker Compose.
- Zona waktu bisnis: Asia/Makassar (WITA). Port web default 8092.



## V1.5.0 Tahap 4.2 — Ruang Kerja Ringkas, Tren Jelas, dan Group Area

- **Viewer/Editor ringkas:** toolbar atas satu baris bila lebar memadai; bilah waktu historis WITA lebih tipis, tombol Putar/Jeda/tanggal/slider tetap ada. Layar Fokus tetap menyembunyikan sidebar. Tombol Fit melakukan zoom terhadap bentang objek.
- **Grafik mini per parameter:** kotak dapat memiliki 1–6 parameter; satu grafik mini selalu diberi nama metrik dan indeks. Klik baris parameter untuk memilih mini-tren. Klik **Lihat tren 24 jam** untuk membuka **pop-up lama yang dipertahankan**, kini dengan opsi Bandingkan Semua apabila satuan identik. Null tetap celah, nol sah.
- **Group Area** (khusus visual): bingkai untuk GI/GH/area pembangkit; solid/dashed/dotted, preset enam warna, opasitas isi 0–40%, label, locked, drag dan resize dengan pegangan sudut. Tidak mempunyai metric/status ataupun hubungan listrik dan selalu digambar di belakang komponen.
- **Kanvas dinamis:** simbol/kotak/area mendekati tepi memperluas kanvas secara bertahap; ukuran manual dapat diatur sampai 20.000 × 20.000 px (grid 10 px), tidak boleh memotong objek. Pan/scroll dan zoom 10–150%. Tidak menggeser objek yang sudah ada secara otomatis.
- Layout lama tanpa `areas` tetap valid. Kontrak JSON hanya menambah `areas` opsional, maks. 100. **Tidak ada migrasi DB**, tidak ada seed maupun auto-connect. Tidak menyentuh readings/hour_records/Formula Engine/Engineering Rules.
- QA: tes backend/JS + pemeriksaan sintaks; build Vite dengan dependency nyata wajib di LXC sebelum dinyatakan layak produksi.

## V1.5.0 Tahap 4.1 — Perbaikan UX Topologi

- **Panel parameter:** kolom properti lebih lebar, daftar terpilih dan pilihan parameter memiliki scroll terpisah; cari parameter berdasarkan nama atau kode.
- **Layar:** halaman Topologi tidak lagi mengikuti batas lebar dan margin putih aplikasi umum. Mode Lihat dan Editor mengisi tinggi viewport dengan panel waktu WITA tetap ada. Tombol **Layar Fokus** menyembunyikan sidebar sementara; tekan tombol Tampilkan Menu atau Escape untuk kembali.
- **Busbar:** admin dapat menyesuaikan panjang dari panel Properti Simbol (input angka/slider, grid 10 px), dibatasi kanvas dan maksimal 1200 px. Panjang hanya mengubah simbol; garis lain tetap manual.
- **Zoom:** tombol zoom di Editor dan Sesuaikan Lebar di Viewer; tidak mengubah koordinat layout atau pembacaan listrik.
- Tidak ada migrasi baru, perubahan pada readings/hour_records, formula, Engineering Rules, atau koneksi otomatis.

## V1.5.0 Tahap 4 — Diagram Builder Lengkap

- Palet 8 simbol kelistrikan; tempatkan via klik atau drag-drop, geser/rotasi/ubah label & asset eksplisit, hapus.
- Gambar garis manual titik demi titik (min. 2, maks. 32), level label `unspecified` atau `20kv`, pindahkan vertex, tambah/hapus titik dan hapus garis.
- Kotak summary, ranking (satuan harus identik), legend, text serta grafik mini 24 jam yang tidak menyambung NULL.
- Diagram tetap tanpa seed koneksi. Mode Lihat semua user, edit admin; versi backend `1.5.0-stage4`, konfigurasi saja.
- Tidak ada migrasi DB/tabel kelistrikan baru. Lihat `README_UPGRADE_V1_5_0_STAGE4.md`.

## V1.5.0 Tahap 3 — Visual Editor Topologi

- Admin dapat membuat diagram baru (kosong) dan menekan **Edit Diagram** tanpa menambahkan sambungan fiktif.
- Kotak parameter dibuat dari Master Parameter aktif, 1–6 kode unik, tanpa menyimpan nilai pembacaan. Peralatan dapat difilter, parameter disusun, dan kotak digeser dengan pointer events (SVG) mengikuti grid 10 px.
- Properti kotak: judul, sumber peralatan, X/Y, lebar, desimal, satuan, rule status aktif, jangkar simbol, locked, duplikat, hapus, serta susunan untuk peralatan sejenis dengan pencocokan nama+satuan **persis** (tak ada tebakan konversi atau hubungan).
- **Buat draf dari daftar peralatan** hanya menempatkan simbol yang dikenali dari jenis peralatan aktif, tanpa garis; tipe yang tidak dikenal dilewati. Tidak ada seed topologi atau status pemutus.
- Urungkan/Ulangi, Reset, Batal, Simpan Perubahan, proteksi perubahan yang belum disimpan, HTTP 409, riwayat revisi dan pulihkan versi menggunakan API Tahap 1 (immutable).
- Tidak ada perubahan skema database baru, data pengukuran, formula, atau rules. Fitur tersebut sudah ditambahkan di Tahap 4 secara manual.
- **Panduan upgrade:** `README_UPGRADE_V1_5_0_STAGE3.md`.

## V1.5.0 Tahap 2 — Mode Lihat Topologi

- Menu **Monitoring → Topologi** dan halaman khusus bertema gelap, mengikuti konsep visual HTML referensi. Seluruh halaman lainnya tetap menggunakan tema BerauLoad lama.
- Pilih diagram tersimpan, tanggal WITA, jam 00–23, tombol Putar/Jeda, refresh, dan zoom. Data hanya berasal dari `GET /api/topology/{id}/data` dan `/series`.
- SVG memvisualisasikan simbol, garis level berizin, dan kotak parameter yang diposisikan mandiri berdasarkan JSON layout. Simbol pemutus hanya netral, tidak dapat diklik untuk membuka/menutup.
- Klik kotak untuk melihat grafik 24 jam dari pembacaan historis. Null tetap `—`, angka 0 tetap 0, celah grafik tidak diinterpolasi. Warna status hanya berdasarkan rule aktif yang direferensikan layout.
- **Diagram awal tetap kosong.** Tidak ada seed topologi atau tombol edit yang belum berfungsi; admin menyusun diagram pada Tahap 3. Backend Tahap 1 tidak diubah kecuali nomor versi API.
- Berkas baru berada di `frontend/src/features/topology/`. Panduan upgrade khusus: `README_UPGRADE_V1_5_0_STAGE2.md`.

## Yang baru pada V1.4.6.1

- **Laporan & Perbandingan → Laporan Standar**: pilihan parameter dari Master Parameter, cari parameter, pilih maksimum/rata-rata/minimum dan dua tahun. Grafik batang + tabel + persentase perubahan mengikuti pilihan.
- Simpan parameter dan agregasi sebagai **pilihan pribadi** atau **default sistem (admin)**; reset pilihan pribadi. Tahun hanya filter sesi berjalan.
- API `/api/compare` masih kompatibel dengan penggunaan lama, dan `standard_report_selections` adalah tabel additive. Laporan Kustom V1.4.6 tidak diubah.
- Panduan upgrade khusus: `README_UPGRADE_V1_4_6_1.md`.

## Yang baru pada V1.4.6

- **Laporan & Perbandingan → Laporan Kustom**: editor berblok Judul, Paragraf, KPI, Grafik, Tabel; pratinjau historis, template pribadi/sistem, duplikasi, arsip, ekspor PDF atau Excel. Menu laporan standar lama tetap tersedia. CSV kolom fleksibel tetap pada Export Data Excel/CSV.
- **Dashboard Builder → Edit Panel → Gaya Panel & Tipografi**: preset Klasik/Gelap/Lembut, warna teks/latar/border, ukuran font judul/angka dan font family, dengan validasi server. Semua panel existing menggunakan tampilan klasik bila belum diatur.
- **Nomor versi dinamis**: footer, panduan, dan Informasi Sistem membaca dari endpoint `/api/health`, menghindari label versi statis tertinggal.

## Instalasi baru

1. Siapkan Debian LXC yang mendukung Docker Engine dan `docker compose`.
2. Ekstrak ZIP Full Source Stage 4.2 ke `/opt/berauload` untuk instalasi baru (jangan pakai untuk menimpa server aktif).
3. `cd /opt/berauload/BerauLoad_V1_5_0_STAGE4_2 && ./deploy/install.sh` untuk instalasi **baru saja**.
4. Simpan akun/password awal secara aman, lalu buka `http://IP-LXC:8092` atau alamat HTTPS internal yang dikonfigurasi.
5. Batasi akses aplikasi ke intranet/VPN atau reverse proxy HTTPS, dan jalankan backup terjadwal.

**Untuk server Stage 4.1 yang aktif, gunakan patch Stage 4.1 → 4.2; jangan gunakan installer.** Ikuti `README_UPGRADE_V1_5_0_STAGE4_2.md`.

## Pengujian

```bash
./deploy/test.sh
cd frontend && npm install --no-audit --no-fund && npm run build
```

Tes backend menggunakan database SQLite QA terpisah; tidak menulis ke PostgreSQL produksi. Setelah build Docker, verifikasi `docker compose ps`, `./deploy/smoke-test.sh`, dan uji langsung di browser.

## Dokumentasi

- `PANDUAN_PENGGUNA.md` — panduan operator/admin/manajemen, termasuk Mode Lihat Topologi.
- `README_UPGRADE_V1_5_0_STAGE2.md` — panduan patch dari Tahap 1, tes penerimaan, rollback.
- `ARSITEKTUR.md` — lokasi modul, sumber data, keamanan dan migrasi.
- `ATURAN_PROYEK.md` — prinsip maintainability.
- `CHANGELOG.md` — catatan versi.
- `QA_STATUS.md` — hasil tes dan batas validasi.

## Batasan

Visual Editor Tahap 4 menyediakan penggambaran jalur manual dan palet simbol penuh, tetapi hubungan yang digambar bukan konektivitas yang terverifikasi otomatis. Viewer tetap ada pada menu Monitoring → Topologi. Laporan Kustom memakai parameter pengukuran tersimpan; belum memiliki blok khusus hasil Historical Calculation/Engineering Rule dan belum melakukan layout bebas ala Word/Canva. Ekspor laporan kustom saat ini PDF/XLSX; CSV kolom bebas tersedia di menu Export Data. Data kosong berbeda dengan nol; dua seri dibandingkan berdasarkan pembacaan pada jam yang sama.

## V1.5.0 Tahap 1 — Backend Topologi (sudah menjadi baseline)

Modul terisolasi `backend/app/modules/topology/` menambah API `/api/topology` untuk konfigurasi diagram satu garis, validasi layout/metric/peralatan/aturan, revisi immutable, dan pembacaan data per jam/24 jam. Tahap 2 menambahkan menu dan Viewer berbasis API tersebut; editor akan dikembangkan terpisah pada Tahap 3.

Diagram baru kosong. Admin membuat dan memperbarui konfigurasi tanpa menyimpan pembacaan listrik; semua user login dapat melihat. API tidak menyediakan aksi operasi pemutus. BerauLoad tetap data per jam WITA, bukan SCADA realtime. Lihat `README_UPGRADE_V1_5_0_STAGE1.md` untuk prosedur staging, backup, rollback.

## BerauLoad 1.6.0 Stage 9a-fix

Hotfix UI Pengukuran Gardu berdasarkan referensi desain HTML, kode duplikat 409, konfirmasi pengurangan jurusan, dialog konflik yang menjaga ketikan, serta editor definisi tanpa prompt. Tidak ada migrasi baru. Petunjuk: `README_UPGRADE_V1_6_0_STAGE9A_FIX.md`. Fitur contoh Stage 9b dalam desain tidak ditambahkan pada hotfix ini.

### Stage 9d1 — Peta, Grafik dan Tampilan Gardu

Pengukuran Gardu memiliki peta distribusi (Leaflet), filter bersama Analisa, kategori/temuan 9b, panel rincian, geolokasi browser, serta lima grafik Recharts di Analisa. Admin global dapat mengatur ubin peta dari UI. Tidak mengubah data ukur maupun rumus. **Kandidat staging**; baca `README_UPGRADE_V1_6_0_STAGE9D1.md` dan `QA_STATUS_STAGE9D1.md` sebelum upgrade ke server operasional.
