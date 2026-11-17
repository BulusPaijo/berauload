## V1.6.0 Stage 8 — Branding dapat diatur (2026-11-17)

- Modul baru `modules/branding` berisi default authoritative, tabel global `app_branding` ber-ID 1, migrasi aditif/idempotent `20261117_16_stage8_branding`, validasi CSRF/admin, audit, publik GET/ETag/cache, unggahan aman melalui Pillow, dan reset.
- UI `features/branding`: context sebelum login dan cache public localStorage aman, judul/icon/theme/meta, logo login/sidebar dan fallback, form admin dengan preview, sanitasi warna kontras, upload/hapus/reset.
- Identitas tampilan dipakai pada kop PDF dan output Excel, nama file unduhan, nama template/help/sidebar/footer, tanpa mengubah penanda teknis `BerauLoad`, kunci format/import, database/Compose/cookie.
- Migrasi tidak memodifikasi pembacaan, status, formula, hak unit, atau dashboard lama. Pillow 12.3.0 dipin untuk pemrosesan gambar; tes serta batas QA tersedia di `QA_STATUS_STAGE8.md`.

## 1.6.0-stage7-hotfix1 (2026-11-16) — Loadtest & Nginx Hotfix

- Runner: hapus impor `Path` lokal yang menutupi impor global dan menghentikan jalur HTTP non-ASGI.
- Fixture: role `system.load`/`system.capacity`, rekaman WITA beberapa hari/tahun, diagram sintetis, pembaca di ULP dengan data, dan kode parameter fixture pada analytics/compare.
- Setiap pembaca mengulang dashboard, analytics, compare, kelengkapan, topologi (`/api/topology`), dan ekspor, dengan jeda 3–8 detik; HTTP non-2xx tak diharapkan serta respons kosong/configured:false menyebabkan GAGAL.
- Laporan jumlah/p50/p95/p99 tiap endpoint, status HTTP, konflik 409 disengaja, pemeriksaan kehilangan data, dan keputusan LULUS/GAGAL sesuai ambang.
- Tambah tes kedua jalur runner (ASGI SQLite dan server HTTP lokal terisolasi), error/payload guard, izin fixture.
- `frontend/nginx.conf` regex hashed assets diberi tanda kutip; `deploy/smoke-test.sh` diberi izin eksekusi.
- Hanya metadata versi `backend/app/main.py` dan `frontend/package.json` yang diperbarui; tidak ada perubahan fungsi aplikasi atau migrasi.

## 1.6.0-stage7 (2026-11-16) — Keandalan Pengisian

- `records`: sparse PUT hour, baseline compare, 409 per parameter,
  PostgreSQL transaction advisory lock, no-op tanpa audit/recalc dan override
  audit; seluruh perubahan sumber/hasil computed tetap dalam transaksi yang sama.
- `sessions`: idle/absolute expiry, touch 5 menit, cleanup, login attempt
  persisted dan migrasi aditif `20261116_17_stage7_session_safety`.
- `frontend`: autosave debounce/blur, antrean per jam, backup, konflik,
  re-login 401, sesi heartbeat/near-expiry, peringatan unload/navigasi.
- `deploy`: DB pool configurable, worker tunggal, nginx gzip/immutable assets,
  keepalive, rate limit login; skrip loadtest isolated.
- Tidak mengubah izin, rekap Stage 5, status final, atau pembacaan lama saat
  migrasi; detail QA dan batas uji di `QA_STATUS.md`.

## V1.6.0 Stage 6 — Matriks Kelengkapan & Telusur Topologi (2026-11-16)

- Tambah endpoint baca-saja kelengkapan 62 hari berizin per unit dan XLSX dua sheet, satu agregasi SQL, status WITA, basis system.load / any_input, NULL ≠ 0, tanpa perhitungan baru atau perubahan migrasi.
- UI Monitoring → Kelengkapan Unit; rentang tanggal, tabel D/V/F per unit/hari, navigasi sel ke Input Harian sesuai hak baca, ekspor XLSX; tes Node untuk logika tampilan.
- Tautan simbol ke diagram unit bawah (validasi keturunan, target aktif, siklus, restore), marker viewer, editor admin dan breadcrumb pada hari/jam identik; saat UP3 dipilih daftar diagram ULP/KP diperlihatkan.
- Skema database, aturan izin, rekap Stage 5, dan pembacaan existing tidak diubah. Status kandidat staging karena npm DNS dan pengujian produksi belum dilakukan.

## V1.6.0 Stage 5 Hotfix 1 — Template Import memicu rekap lintas unit (2026-11-16)

- Panggil `recalculate()` setelah seluruh nilai input+computed lokal yang benar-benar disimpan pada tiap jam template import; kumpulkan perubahan dari penyisipan nyata, bukan semua kode unggahan. Sekali per jam di transaksi yang sama, bukan sekali per kolom.
- Hari KP yang bukan draft tetap dilewati. Hasil ULP verified/final tidak diubah; penanda `source_changed_after_final` tetap melalui modul Stage 5. UP3 dihitung ulang berdasarkan sumber terbaru.
- Tambah 5 tes SQLite sintetis: computed KP→ULP→UP3, NULL operand/kelengkapan, ULP final, rollback sumber+batch+arsip saat hitung ulang gagal pada jam berikutnya, dan skip hari KP terkunci. Tidak mengubah tes lama.
- Benchmark *commit service* 31 × 24 jam (744 jam) dengan satu formula ULP dan satu formula UP3: sebelumnya 9,751 detik dengan 0 hasil rekap; sesudahnya 13,036 detik dengan 744 hasil rekap per unit atas (penambahan 3,285 detik, sekitar 33,7%). Angka lokal SQLite sintetis, bukan SLA LXC PostgreSQL.
- Tidak ada migrasi baru, aturan izin baru, perubahan basis data historis, ataupun fitur frontend baru. Version metadata diperbarui. npm/Vite belum lulus di host pengembangan karena DNS `registry.npmjs.org` gagal.

## V1.6.0 Stage 5 — Data Unit Bawah untuk Unit Atas (16 November 2026)

- **Rujukan parameter hanya ke bawah:** konfigurasi ULP dapat memakai parameter ULP/KP bawahannya; UP3 boleh memakai parameter ULP dan KP; KP tidak dapat melihat parameter ULP/UP3 atau KP setingkat. Validasi server terpusat untuk dashboard, topologi, formula, perhitungan historis, engineering rules, report dan export. Ini rujukan **baca saja** dan tidak memberikan jalur tulis.
- **Pemilihan UI:** katalog parameter menampilkan nama `Unit - Parameter` dan kelompok per unit; Formula Builder memiliki bantuan memilih parameter role yang sama dari bawah, namun daftar operand tetap eksplisit dan dapat diedit. Tidak ada rekap otomatis.
- **Rekap aktual:** pada penyimpanan pembacaan manual/import, formulasi aktif yang terdampak dihitung berurutan secara deterministik dalam **transaksi yang sama** dengan pembacaan. NULL operand menahan hasil menjadi NULL, sedangkan 0 dihitung 0. Completeness `/api/formulas/completeness` menunjukkan `n dari m sumber terisi`.
- **Perlindungan status:** hari ULP verified/final tidak ditimpa. Tabel tambahan `unit_source_changes` mencatat perubahan sumber pada hari terkunci; verifier/admin melihat pemberitahuan melalui status hari, dan admin dapat membuka kembali untuk menghitung ulang jam yang ditandai. UP3 tidak mempunyai status hari dan mengikuti pembacaan terkini; status sumber terinci ditampilkan melalui API dan UI.
- **Finalisasi saat KP draft:** perlu konfirmasi eksplisit dan audit `finalize_with_draft_sources`. Penanda status sumber ditampilkan di panel, topologi, laporan, export, historical, dan engineering.
- Migrasi skema `20261116_16_stage5_source_changes` additive, `schema_migrations`, tanpa perubahan/bagi ulang data lama pada startup. Tidak ada konfigurasi unit, kode, formula lama, atau nilai rekaman verified/final yang dibackfill.
- QA lengkap di `QA_STATUS.md`; kandidat staging, belum tervalidasi browser/PostgreSQL produksi atau build npm pada environment ini.

## V1.6.0 Stage 4c UI Hotfix 1 — Pengguna (2026-11-16)

- Frontend Pengaturan → Pengguna: pisahkan **Jenis akun** (Role global) dan **Akses unit** (checkbox per unit); peran unit berlabel hanya muncul setelah unit dicentang.
- Jenis akun admin menyembunyikan akses unit dan menampilkan `Admin berlaku untuk semua unit`; non-admin tanpa unit diberi pesan validasi sebelum pengiriman.
- Daftar Pengguna kini menampilkan nama unit serta peran dari endpoint admin `/api/org-units/{id}/access` yang sudah tersedia. Tidak menambah endpoint, hak akses, atau migrasi.
- Manajemen UI dipindah ke `frontend/src/features/users/`, dengan tes Node sintetik. Metadata VERSION/frontend/API health diperbarui konsisten.
- QA: `npm install` gagal karena DNS `EAI_AGAIN`; build frontend belum lulus / belum siap produksi.

## V1.6.0 Stage 4c — Frontend & Pengguna (kandidat staging, 15 November 2026)

- Pemilih unit di sidebar, `X-Unit-Id` terpusat, fallback localStorage dan isolasi state halaman per unit; penanda baca-saja/admin UP3, informasi parameter utama tidak disetel.
- Status/verifikasi/finalisasi hari menyertakan pelaku dan penanda admin; preview verify-tree/finalize-tree sebelum commit, KP kosong dilewati dengan alasan; 422 bila tak ada unit yang dapat diproses.
- Akses pengguna eksplisit, multi-unit/peran, validasi unit aktif, pengubahan/pencabutan akses, preservasi akses admin historis.
- Pengaturan Salin Pengaturan per unit dengan pratinjau pemetaan kode dan peringatan data yang tidak disalin.
- Fallback preferensi chart dan laporan pribadi dari `scope=user` pada unit non-home tanpa mutasi DB.
- QA: 125 backend tests + 4 Node tests lulus, 56 file TS/TSX lolos syntax transpile (bukan typecheck); `npm install` gagal `EAI_AGAIN` dan `npm run build` belum lulus karena dependensi tidak tersedia. Belum divalidasi di PostgreSQL/browser LXC.

## V1.6.0 Stage 4b — Konfigurasi per Unit (2026-11-15)

- `org_units/migration_config.py`: kolom `unit_id` nullable/FK pada tab, placement, revisi form, dashboard, chart settings, topology, export, report, standard reports, formula, historical, engineering dan audit. DDL additive idempotent dijalankan sebelum migrasi ORM lama. Backfill konfigurasi ke `legacy_home` **hanya sekali** melalui `schema_migrations` versi `20261115_16_unit_configuration_stage4b`; audit log lama tetap `NULL`. Jumlah konfigurasi pribadi yang tidak bisa dipastikan dicatat pada startup log dan dikaitkan ke legacy_home, bukan ditebak.
- Konfigurasi dibaca dan ditulis hanya pada `X-Unit-Id` aktif; ID milik unit lain mengembalikan 404. Hak baca mengikuti 4a, sedangkan perubahan konfigurasi hanya oleh admin global (cookie dan CSRF tetap wajib). UP3 boleh dashboard, topologi, computed; UP3 menolak form input.
- Tab default unit baru dibuat saat admin membuat ULP/KP, bukan pada setiap startup. Kode tab baru menggunakan prefiks ID unit agar constraint unique lama tidak perlu diubah. Pengaturan `system`/`user` tambahan memakai scope internal berbeda per unit untuk mempertahankan constraint global yang lama; nilai scope API tetap seperti sebelumnya.
- Admin API `POST /api/org-units/{id}/copy-settings/preview|commit`: pemetaan kode tanpa awalan sumber menjadi `<kode_tujuan>_<kode_lama>`, atau mengganti awalan sumber dengan kode tujuan; menolak kode bentrok, unit tujuan yang sudah berisi data, referensi luar unit, serta diagram ber-Engineering Rule yang tidak disalin. Salin asset, input metric, formula computed yang punya definisi, tab/placement form, opsional diagram; tidak menyalin readings, HourRecord, day states, batches, ataupun dashboard pribadi. Commit satu transaksi, audit sumber/tujuan/jumlah.
- `legacy_home_scope` dihapus setelah seluruh router konfigurasi memakai context per unit. Tahap 4c pemilih unit UI dan Tahap 5 referensi lintas unit **belum dibuat**.
- QA: 122 tes backend dan 31 tes JS lulus memakai SQLite sintetis; npm install gagal DNS EAI_AGAIN, npm build gagal karena dependencies belum terpasang; Docker/PostgreSQL 16/browser belum diuji pada kandidat 4b.

## V1.6.0 Stage 4a — Konteks Unit, Izin, dan Data Operasional (2026-11-15)

- `org_units.context.unit_context(mode)` memproses header `X-Unit-Id`, unit default, hierarki serta izin baca/menulis tanpa mempercayai ID unit dari klien. Admin global dapat bertindak sebagai operator/verifier pada ULP/KP; UP3 tidak menginput dan tidak punya status hari.
- `records.service` memakai status `unit_day_states`, mencerminkan ke `day_states` hanya untuk legacy_home. Endpoint verify/finalize/reopen dan bulk verify-tree/finalize-tree memakai transaksi atomik serta audit aktor/unit/peran.
- Ekstraksi endpoint katalog, input jam, import laporan lama, analitik, dashboard, compare dan laporan ke modul domain; URL lama dipertahankan. Filter unit di katalog, pembacaan, monitoring, laporan, template import. Tidak ada perubahan source importer.py, rumus teknis, nilai pengukuran, maupun struktur DB.
- Konfigurasi lama belum mempunyai `unit_id` tersendiri; akses konfigurasi legacy dibatasi agar tidak bocor ke unit lain sampai 4b. Frontend pemilih unit dijadwalkan 4c; frontend tidak berubah pada 4a.
- Tes keamanan lintas unit menggunakan SQLite sintetis. Dua fixture/asersi lama yang bertentangan disesuaikan: test_org_units_home.py (management berada di UP3) dan test_template_import.py (status serta riwayat batch harus memiliki unit_id). Tes can_write juga disesuaikan menjadi inherited write ULP→KP sesuai aturan baru. Rincian dan hasil aktual di QA_STATUS.md.

## 2026-11-15 — V1.6.0 Stage 3: Parameter Utama per Unit

- Tambah `org_units/roles.py` dengan `metric_for_role(db, unit_id, role_key)` (nullable) dan peta `roles` pada `/api/catalog`. Role beban sistem `system.load` dan daya mampu `system.capacity` menggantikan **seluruh default operasional** yang sebelumnya merujuk kode keras; sumber H/J yang asli tidak diganti.
- Tambah Pengaturan admin **Parameter utama unit** (`/api/primary-metrics` GET/PUT), hanya memilih metric aktif unit `legacy_home`, menolak konflik peran, menyimpan audit, tanpa menulis data pembacaan.
- Endpoint lama dashboard, analytics, compare, records/day, laporan PDF/Excel, monitoring, dashboard_charts, standard_reports, serta Dashboard Builder default & validasi pasangan H/J menerima role terpilih. Role tidak ada → `configured:false`, nilai tidak tersedia (null), tanpa HTTP 500. Konfigurasi tersimpan/revisi tidak diubah diam-diam.
- Tambah inventaris referensi `GET /api/metrics/{id}/usage` dan konfirmasi eksplisit sebelum menonaktifkan parameter yang dipakai. Topologi ‘Terapkan ke Peralatan Sejenis’ mengutamakan role_key pada unit sama lalu fallback nama+satuan.
- Modularisasi route lama dari `main.py` ke `analytics_core`, `records`, `legacy_reports`, `parameters`, `users` dengan URL, CSRF, audit, dan perilaku lama dipertahankan. Frontend mengonsumsi `catalog.roles` dalam Monitoring, Dashboard Builder, Historical, Engineering Rules, Formula, Standard Reports, Export serta teks default.
- Tidak ada migrasi database baru; tidak mengubah `catalog.py`, `importer.py`, migrasi seed lama, saved JSON/formula, `readings`, `hour_records`, `day_states`.
- QA: tes backend lama 103 + lima tes baru 108 lulus; Node 29 tes lama + 2 tes baru role-matching 31 lulus (`--experimental-strip-types`); `npm install` gagal `EAI_AGAIN`, `npm run build` gagal sebab dependensi tidak tersedia, Docker/PostgreSQL/browser belum diuji. Status **kandidat staging**.

---

## 2026-11-15 — V1.6.0 Stage 2: Import Template

- Backend modul `template_import` (`migrations`, `repository`, `workbook`, `validator`, `service`, `router`) dengan unit_id eksplisit, XLSX harian WITA (maks. 92 hari), validasi kode baris 3, `_meta`, duplikat, value finite, dan formula injection di seluruh workbook.
- Pratinjau perubahan non-destruktif: `fill_empty`/`new_hours`, statistik per parameter, 200 perbedaan, konflik hari final/verified. Commit single transaction, staging token, SHA256+unit 409, archive XLSX, audit dengan user dan unit; perhitungan computed hanya untuk nilai yang belum tersedia.
- Migrasi `20261115_13_template_import_batch_kind`: nullable `import_batches.kind`, backfill lama satu kali, index unik parsial batch template per unit+SHA256. Tidak ada perubahan importer/endpoint lama maupun parameter teknis.
- Frontend Import Excel menjadi tab **Template BerauLoad** dan **Laporan lama**; isi komponen lama dipertahankan. Riwayat pada tab baru menampilkan jenis.
- `VERSION`, FastAPI `/api/health`, dan frontend `package.json` menjadi `1.6.0-stage2`. Full QA dan batas yang belum diuji di `QA_STATUS.md`.

# V1.6.0-stage1.2 (2026-11-15) — Guard Migrasi Sekali Jalan

- `org_units/migration_home.py`: jalankan DDL additive `legacy_home`/index pada setiap startup, tetapi seed/pindah asset/metric/import/status/akses dan audit **hanya jika** `20261115_12_legacy_home_ulp_tanjung_redeb` belum ada di `schema_migrations`.
- `org_units/migrations.py`: `_copy_states_and_users()` hanya dijalankan saat `20261115_11_org_units_stage1` belum ada; perbaikan `unit_id IS NULL` pada assets/metrics/import_batches tetap tersedia.
- Perbaiki dua asersi dalam `test_org_units.py::test_api_hierarchy_csrf_access_and_audit` sesuai kebijakan seed ULP/akses non-admin. Tambah `test_org_units_stage12.py` untuk uji `setup()` berulang, data computed UP3, akses beda peran, akses ULP lain, dan tiga jalur migrasi; angka pengukuran tetap.
- Tidak ada migrasi schema baru, endpoint, perubahan frontend UI, role global, formula, atau topologi. Nomor versi aplikasi dan dokumentasi diperbarui.
- QA: 80 backend, 27 JavaScript lulus; npm install gagal DNS dan npm build gagal karena dependensi tidak tersedia; PostgreSQL/Docker/browser tetap harus diuji di LXC.

---

# V1.6.0-stage1.1 (2026-11-15) — Legacy Home ULP Tanjung Redeb

- `org_units.legacy_home` boolean default false + indeks unik parsial; seed satu ULP `ulp_tanjung_redeb` di bawah UP3 jika belum ada.
- Migrasi SQL idempotent/transactional dua jalur (Stage4.2 melalui Stage1, atau Stage1 langsung); pindah FK kepemilikan asset/metric/import_batch/mirror status dari UP3 ke ULP. User non-admin akses root dipindahkan ke ULP; admin tetap di UP3.
- `repository.root()` berdasarkan level, `home_unit()` tunggal. Default pembuatan data lewat API, formula computed, import batch, status mirror, dan seed memakai ULP; pembuatan user admin tetap root.
- Tidak mengubah data asli, Formula Engine, Historical Calculation, Engineering Rules, Topologi, nilai H/J, Global Role, atau panel UI selain adanya unit ULP di Pengaturan.
- QA: 75 tes backend lulus, 1 tes Stage1 lama tidak kompatibel; 27 tes JS lulus. npm install gagal DNS, npm build gagal karena dependensi tidak ada. Belum teruji Docker/PostgreSQL/browser LXC.

---

# BerauLoad V1.6.0 Tahap 1 — Fondasi Multi-Unit (2026-11-15)

- Tambah `org_units`: UP3 tunggal seed `up3_berau`, ULP di bawah UP3, KP di bawah ULP, tanpa unit lain otomatis. Kode/level tak berubah, tidak ada delete, validasi kuota dan anak aktif, audit semua perubahan.
- Migrasi additive/idempotent (`schema_migrations`), kolom FK `unit_id` nullable di assets/metrics/import_batches + `metrics.role_key` nullable dengan unique index per unit. Backfill semua data legacy ke UP3; hanya dua key `system.load` & `system.capacity`.
- `unit_day_states` salinan UP3 dan dual-write atomik pada verify/finalize/reopen; tetap membaca `day_states`, `readings`/`hour_records` tidak berubah.
- `user_unit_access` backfill setiap pengguna ke UP3 sesuai role global. API `/api/org-units` dan UI admin Pengaturan → Struktur Organisasi (tree dan akses pengguna). Izin operasional lama **belum dibatasi** dan tidak ada pemilih unit.
- Katalog menambahkan `unit_id` dan `role_key`, PUT Metric menerima key opsional tanpa memengaruhi update lama. Create API lama otomatis di-link ke UP3.
- Stage 4.2 Topologi, report, H/J dan frontend lainnya tetap utuh. QA terbatas SQLite/pure JS, wajib build Docker/Postgres/browser di LXC.


---

# BerauLoad V1.5.0 Tahap 4.2 — Compact Workspace, Multi-Metric Trends & Visual Group (2026-11-15)

- Header Viewer dan bilah waktu WITA diringkas, tetapi pemilih diagram, admin Edit, fokus, zoom/Fit, reload, tanggal, Putar/Jeda dan slider tetap tersedia. Editor memiliki tombol Fit dan zoom minimum 10%.
- Grafik mini kotak secara eksplisit mengikuti parameter yang diklik. Pop-up grafik lama tetap ada; opsi Bandingkan Semua menampilkan garis berlegenda untuk parameter bersatuan identik saja. Jam kosong tidak diinterpolasi; pembacaan 0 tetap 0.
- Group Area untuk pengelompokan GI/GH/pembangkit: solid/dashed/dotted, warna preset dan transparansi, drag, resize, label dan locked. Hanya elemen gambar yang tidak memengaruhi data atau konektivitas.
- Kanvas otomatis bertambah saat drag/penempatan mendekati batas, tersedia ukuran manual/fit objek hingga 20.000 px per sisi. Group Area pada layout adalah array opsional, limit 100, validasi server ketat; layout Stage 4.1 tetap sah.
- Tanpa migrasi baru, tanpa seed atau status pemutus, tidak menyentuh `readings`, `hour_records`, formula maupun Engineering Rules. Patch hanya dari Stage 4.1.
- Tes QA dicatat pada `QA_STATUS.md`. Build npm/Docker/browser nyata wajib diverifikasi di staging LXC.

# BerauLoad V1.5.0 Tahap 4.1 — Topology UX Hotfix (2026-11-15)

- Daftar parameter di Properti Kotak mendapat input cari, lebar panel diperbesar dan scroll terpisah sehingga nama dan pilihan tidak terpotong.
- Mode Editor dan Mode Lihat mengisi viewport tanpa margin halaman umum. Tombol Layar Fokus dapat menyembunyikan sidebar, Escape untuk kembali.
- Busbar memiliki kontrol panjang numerik/slider, tersnap grid 10 px dan dibatasi lebar kanvas; garis listrik lain tidak dimodifikasi otomatis.
- Zoom Editor serta Sesuaikan Lebar Viewer; mode data per jam WITA, NULL dan pembatasan akses tetap.
- Tanpa migrasi baru, tanpa perubahan skema, data, formula dan status PMT. Patch hanya dari stage4.

# BerauLoad — Changelog

## V1.5.0 Tahap 4 — Diagram Builder Lengkap (2026-11-15)

- Palet 8 simbol: generator, incoming, busbar, breaker (netral), transformer, feeder, load dan capacitor. Admin menambah dengan klik pada kanvas atau HTML drag-drop, lalu memindahkan, memberi label, mengaitkan ke master peralatan secara eksplisit, memutar dan menghapus simbol.
- Garis baru **hanya** dibuat manual oleh admin: klik beberapa titik pada kanvas lalu Selesaikan Garis, atau Batalkan Garis. Pilih level visual `unspecified`/`20kv` dari whitelist; pilih garis untuk memindahkan/menambah/menghapus vertex dan menghapus garis. Garis tidak mengklaim kontinuitas listrik atau status energized.
- Jenis kotak `metric`, `summary` (jumlah pembacaan tersedia + nilai asli), `ranking` (peringkat nilai per jam dengan satuan identik), `legend` (keterangan level gambar), `text` (judul/catatan). Tidak ada agregasi lintas satuan/threshold fiktif.
- Grafik mini membaca `/api/topology/{id}/series?day=...` (24 jam) yang sudah ada, tidak menyambung jam kosong; angka nol tetap nilai yang sah. Endpoint jam/series dimuat ulang setelah menyimpan layout.
- Validasi backend untuk peringkat bersatuan identik, jenis kotak, dan titik berurutan yang tidak boleh sama. Tidak ada migrasi DB baru, tabel pengukuran/tahap sebelumnya tidak berubah. CSRF, admin-only write, audit, revisi immutable dan HTTP 409 tetap digunakan.
- QA sintetis: 63 backend + 17 frontend pure JS passed; parser 46 file TS/TSX bersih; pemeriksaan tipe terfokus dengan shims bersih. `npm install` gagal DNS `EAI_AGAIN`, sehingga build Vite/Docker/browser belum diverifikasi dan wajib dites di LXC.

---

## V1.5.0 Tahap 3 — Visual Single Line Editor (2026-11-14)

- Editor admin untuk membuat diagram kosong, menambah kotak parameter, mengubah properti (1–6 metric per box), drag SVG snap 10 px, urut parameter, duplikasi/hapus, kunci posisi, dan mengaitkan rule status aktif.
- Draft lokal hingga Simpan; Batal/Reset, Undo/Redo, peringatan keluar halaman, `expected_version` dan HTTP 409. Riwayat revisi bisa dipulihkan sebagai versi baru dengan API Tahap 1.
- Buat draf dari master peralatan hanya membuat simbol, **tanpa wires** atau klaim jaringan. Pencocokan lintas peralatan harus sama persis pada nama+satuan. Legacy daya mampu manual tidak dapat dipilih.
- Viewer Tahap 2 tetap tersedia untuk semua pengguna. Menu Topologi adalah satu-satunya perubahan navigasi yang dipakai; struktur database dan backend kelistrikan tidak berubah.
- QA: tes regresi backend, tests JS murni editor/viewer, sintaks frontend; build npm/Vite/Docker aktual diwajibkan di staging LXC.

---

# V1.5.0 Tahap 2 — Single Line Viewer (2026-11-14)

- Monitoring → Topologi: Viewer SVG gelap, pemilih diagram, zoom dan refresh; tanggal/jam WITA 00–23 dengan Putar/Jeda.
- Simbol/garis/kotak membaca layout tervalidasi dari backend Tahap 1. Kotak dan simbol tetap objek berbeda. Tidak ada fungsi ubah konfigurasi maupun kontrol pemutus.
- GET data per jam dan tren 24 titik mengikuti backend existing; angka 0, NULL, dan status rule aktif ditangani tanpa asumsi teknis.
- Modal grafik historis untuk kotak berparameter; tren mempertahankan jam kosong.
- Diagram kosong ditampilkan sebagai keadaan kosong; tidak ada topologi Berau yang disemai.
- UI tema dark khusus Topologi. Kontrak database, readings, formula, dan Engineering Rules tidak berubah; versi API `1.5.0-stage2`.
- 4 tes Node khusus formatter/tren dan regresi Python; lihat QA_STATUS.md. Build React lengkap dan browser LXC masih memerlukan uji aktual.

# V1.5.0 Tahap 1 — Topology Backend (2026-11-14)

- Domain baru `topology`: model TopologyDiagram/TopologyRevision, migrasi additive/idempotent tanpa seed, validasi layout murni.
- API login-only read dan admin-only write dengan CSRF, CAS `expected_version`, audit, revisi immutable dan soft archive.
- Endpoint read-only data per jam dan series 24 jam. Zero≠NULL, evaluasi status memakai Engineering Rules V1.3, tidak mengubah readings/formula.
- Batas whitelist simbol, ID, grid, referensi peralatan/parameter aktif; menolak parameter legacy daya mampu.
- Backend Tahap 1 selesai; viewer/editor/garis interaktif dan menunya belum tersedia. Belum ada seed koneksi listrik atau kontrol pemutus.
- Lihat `QA_STATUS.md` dan `README_UPGRADE_V1_5_0_STAGE1.md` untuk hasil pengujian dan batas rilis.

## V1.4.6.1 — Standard Report Parameter Selector (2026-11-14)

- Laporan Standar: perbandingan satu parameter Input/Computed yang aktif untuk dua tahun, pilihan MAX/AVG/MIN dan pencarian, grafik/tabel mengikuti satuan parameter.
- Preferensi parameter dan agregasi per pengguna serta default sistem admin; audit dan migrasi additive/idempotent.
- Endpoint `/api/compare` kompatibel dengan versi sebelumnya; `peak_growth_pct` tetap tersedia, ditambah `growth_pct` sesuai agregasi.
- Tidak mengubah data historis, formula, laporan kustom, dan Dashboard Builder.
- Tes baru untuk data kosong, nol, parsial, auth, migrasi dan metode agregasi.

## V1.4.6 — Report Builder & Panel Styling (2026-11-14)

- **Laporan → Laporan Kustom:** template laporan sistem/pribadi, tambah/reorder blok judul, paragraf, KPI, grafik dan tabel, pratinjau sumber data asli, ekspor PDF/XLSX, duplikasi/arsip. Laporan standar V1.4.5 tetap tersedia.
- **Dashboard Builder:** preset Klasik/Gelap/Lembut, font, ukuran judul dan KPI, warna teks/latar/border melalui UI. Setting disimpan dalam JSON layout existing dan divalidasi backend; data pengukuran tidak berubah.
- `report_templates` dibuat lewat migrasi additive/idempotent dengan audit aktivitas. Scope sistem hanya admin, personal terbatas pada pemilik, version check pada pembaruan.
- Grafik laporan berpasangan hanya menggunakan jam dengan kedua pembacaan; interval kosong tetap kosong, nol valid tetap nol.
- Nomor versi footer, Panduan Pengguna dan Informasi Sistem kini mengikuti `GET /api/health`, mengurangi risiko label versi tertinggal.
- Test backend khusus report PDF/XLSX, akses, revisi, migrasi dan style whitelist; lihat `QA_STATUS.md`.

## V1.4.5 — Visual Layout Editor (V1.4.4.1) + Performance

- Desktop: sudut panel dapat ditarik untuk resize lebar/tinggi dengan snap-to-grid 12 kolom; drag pegangan untuk menyusun urutan, tombol arah/dropdown tetap tersedia. Batal, Simpan dan Reset versi tersimpan tetap bekerja.
- Kontrak layout diperluas secara backward-compatible menjadi lebar 3–12 kolom dan tinggi 1–4 tingkat. Tidak ada schema DB baru.
- API baca gabungan `/api/performance/series` untuk maksimal empat parameter yang menghindari N permintaan terpisah pada grafik; hasilnya diuji identik dengan `/api/analytics` V1.4.4.
- Cache ringkas dalam satu proses (maks. 128 entri / 45 detik) dengan invalidasi segera setelah commit input harian atau import. Batas data kosong/0 tetap dipertahankan.
- Export CSV/XLSX berurutan tetap memakai streaming file dari V1.4.4. Tidak ada formula/rule/measurement yang dimodifikasi.
- Tes backend dan geometri UI serta panduan upgrade diperbarui.

# Changelog BerauLoad

## V1.4.4 — Dashboard Management & Custom Export Data (2026-11-14)

- Dashboard Management: tiga template awal (Operasi/Pembangkit/Feeder), impor dan ekspor konfigurasi JSON, berbagi dashboard pribadi baca-saja kepada username tertentu, pencabutan akses, riwayat layout dan pemulihan sebagai revisi baru.
- New modular `data_export`: pemilihan parameter/kolom dan urutan, judul kolom, resolusi jam/hari/bulan/tahun, agregasi AVG/MIN/MAX, konversi tampilan sesuai dimensi satuan, pratinjau, ekspor XLSX/CSV, serta template pribadi/bersama yang dapat diperbarui dan diarsipkan.
- Migrasi additive/idempotent: `export_templates`, `dashboard_revisions`, `dashboard_shares`. Backfill snapshot hanya untuk versi layout existing yang saat migrasi masih tersedia.
- Perbandingan H/J pada Dashboard utama tetap sama, tidak ada perubahan pada `readings`, Formula Engine, Historical Calculation, atau Engineering Rules. Ekspor agregat per parameter, bukan otomatis agregasi H/J berpasangan.
- Tes regresi backend diperluas; lihat `QA_STATUS.md` untuk bukti dan batas validasi.

## V1.4.1 — 2026-11-14
- Dashboard Builder: edit mode memiliki Batal dan Reset ke Tersimpan dengan draft lokal; tidak membuat update server sebelum Simpan.
- Dashboard utama kini menggunakan default dashboard (pribadi > sistem) dan menyediakan tampilan klasik.
- Pencarian, filter status dan pagination terpusat untuk Perhitungan Historis, Engineering Rules, Peralatan, dan Parameter.
- Jenis Peralatan menjadi master yang dikelola admin, melalui tabel baru `equipment_kinds` dan migrasi additive/idempotent. Kode jenis yang sudah dipakai tidak diganti.
- Tidak mengubah pengukuran, formula Excel-like, kondisi final, atau perbandingan daya mampu H vs beban J.
- Penambahan tes otomatis pengelolaan kategori dan hak akses, serta pembaruan Panduan Pengguna.
- Status QA: 26 tes backend lulus; build npm/Vite dan Docker/PostgreSQL aktual belum diverifikasi.

# BerauLoad Change Log

## V1.3.0 — 2026-11-14
- Engineering Rules modular: `models/repository/service/router/migrations` terpisah dari Formula Engine V1.1 dan Historical Calculation V1.2.
- Rule Builder via UI, simulasi, Draft/Active/Archived, versioned revisions dengan approval admin, evaluasi historis, missing-data accounting.
- Tidak ada default batas operasi dan tidak ada alert atau otomasi kontrol real-time; hasil evaluasi hanya advisory.
- Tambahan empat test suite regresi (20 total tes Python lulus).

## V1.2.1 — 2026-11-14
- Revisi formula historis dengan immutable revision snapshot dan optimistic version check; archive/restore serta audit.
- Migrasi idempotent dari tabel historical_definitions V1.2.0 tanpa mengubah pembacaan lama.
- Perhitungan bisa memakai versi sebelumnya secara eksplisit lewat API dan UI.

---

# CHANGELOG

## V1.2.0 — Historical Calculation Engine (2026-11-13)
- Menambahkan definisi rumus historis immutable, preview tanpa simpan, run per periode dan UI Analisis Beban → Perhitungan Historis.
- Memakai engine matematika/AST V1.1 yang sama (cache parse tanpa mengubah semantik); bukan interpreter baru.
- Agregasi AVG, MAX, MIN; SUM hanya indikator tanpa dimensi, time-window WITA, moving average kalender ketat, dan YoY bulanan dengan flag keterbandingan.
- Migrasi additive `20261113_03_historical_calculations`, endpoint admin/read-only, audit pembuatan, tes QA batas & integrasi Excel November.
- Tidak mengubah data historis, formula bawaan, kolom H/J, ataupun aturan finalisasi.

## V1.1.3 — Master Peralatan UX (2026-11-13)
- Mengganti prompt browser Tambah Peralatan dengan drawer responsif, auto-suggest kode, pencarian/filter, dan edit nama/status.
- Kode dan jenis peralatan yang sudah dipakai terkunci; tidak ada migrasi atau perubahan API.


## V1.1.2 — Parameter Drawer & Dashboard Series Preferences (2026-11-13)
- Tambah/Edit Parameter via side drawer; untuk computed me-reuse Formula Builder dan API V1.1, tanpa engine kedua.
- Edit metadata nama/aktif parameter existing; ekspresi formula existing tetap immutable.
- Grafik pilihan 1–4 parameter yang mempunyai satuan sama, dengan perbedaan default sistem (admin), preferensi pribadi, dan sementara.
- Grafik default H/J tetap menggunakan metode perbandingan jam berpasangan V1.1.1; seri lain diambil dari API analytics existing.
- Migrasi additive `20261113_02_dashboard_chart_settings`, audit perubahan pengaturan.
- Hotfix TS2531 pada SystemLoadCompare sudah terintegrasi.
- Uji backend regresi dan konfigurasi: 10 passed; TypeScript syntax parsing lulus. Build npm/Docker end-to-end belum tervalidasi.

# CHANGELOG

## 1.1.1 — Koreksi mapping Daya Mampu Sistem (13 November 2026)
- Grafik daya mampu menggunakan data historis kolom H rekap (`daya_pasok_pembangkit_kw`), bukan input tambahan `daya_mampu_sistem_kw`.
- UI membantu menjelaskan sumber data tanpa meminta pengukuran ganda.
- Contoh formula baru menggunakan kode kolom H.
- Parameter V1.1 legacy dan seluruh pembacaan/formula pengguna dipertahankan; tidak ada migrasi DB.
- Menambah regression test import Excel H/J ke monitoring.

# CHANGELOG

## 1.1.0 — Formula Builder Core + Capacity Comparison (2026-11-13)
- Menambahkan Formula Builder melalui UI (visual dan teks Excel-like), preview, dan validasi formula/satuan/dependensi.
- Formula numeric baru aman dengan AST whitelist: `+ - * /`, perbandingan, `SUM/AVG/MIN/MAX/IF/ABS/ROUND/AND/OR`.
- Rumus baru disimpan sebagai parameter `computed` dengan versi immutable 1; formula rekap V1 tidak diubah.
- Parameter input `daya_mampu_sistem_kw` ditambahkan tanpa nilai default atau backfill.
- Grafik dashboard Daya Mampu vs Beban dengan pilihan harian (24 jam), bulanan (harian), tahunan (bulanan), dan multi-tahun.
- Tambah endpoint `/api/formulas` dan `/api/monitoring/capacity-vs-load`.
- Skema baru additive `formula_definitions` dan `schema_migrations` melalui migrasi idempotent; tidak mengubah tabel historis.
- Memperbaiki ikon `Waveform` yang tidak tersedia menjadi `AudioLines` pada frontend V1.
- Menambah tes rumus dan API, dokumentasi arsitektur, aturan proyek, serta upgrade script V1.0.

## 1.0.0 — Initial Release
- Input beban per jam, parser/import Excel, dashboard historis, laporan, pengaturan, audit, role, dan Docker Compose.

## V1.4.0 — Dashboard Builder Core & Panduan Pengguna (2026-11-14)

- Added domain `dashboard_builder` with additive migration, seeded Berau default (H/J), CRUD, clone, per-scope default, soft archive, audit, server-side permissions, and atomic optimistic version update.
- Added `Dashboard Builder` frontend with custom line/area/bar/stat/gauge/table/rule panels, metric/historical/engineering sources, global date range, mobile-friendly layout reorder/resize, and drawer editor.
- Preserved V1.3 dashboard and all electrical calculations; capacity continues from Excel REKAP H and load from J with only paired hourly values.
- Added complete `PANDUAN_PENGGUNA.md`, searchable in-app help, browser print support, `README_UPGRADE_V1_4.md` and backend regression tests.
- Known limitations: registry npm inaccessible in development environment; full `vite build`/Docker LXC smoke test must run in staging; no sharing by group or dashboard config export/import in V1.4.0.

## V1.4.2 — 2026-11-14
- Pengaturan berurutan untuk pengguna awam dengan navigasi Peralatan → Parameter → Form Input → Dashboard.
- Dynamic Input Form: tab custom/nama/urut/aktif, kolom parameter dipindah/diurut/tampil-sembunyi dari UI; Simpan/Batal dan pratinjau.
- Parameter INPUT baru dapat memilih tab langsung; Formula Engine existing, identitas Metric/kelompok sumber, data, dan import H/J tidak berubah.
- Tiga tabel konfigurasi additive dan idempotent; optimistic concurrency & audit; backend regression dan tes batas.
- Panduan penggunaan, arsitektur dan petunjuk upgrade diperbarui.

## V1.4.3 — 2026-11-14 (kumulatif V1.4.2.1 + Advanced Visualization)
- **V1.4.2.1 — Master Satuan**: master immutable kode/dimensi/faktor konversi, custom unit melalui UI, dropdown satuan Parameter/Formula/Historical/Engineering, endpoint preview konversi, audit dan migrasi additive.
- Formula Engine V1.1 tetap menjadi interpreter AST yang aman; lapisan unit-aware mengizinkan perhitungan numerik antar-satuan kompatibel (MW/kW), menolak kW/kVA dan data kosong, tanpa `eval` atau perubahan rumus rekap Excel.
- Historical Calculation V1.2 dan Engineering Rules V1.3 memakai lapisan validasi satuan yang sama untuk definisi baru; hasil arsip lama dan data dasar tetap dipertahankan.
- **V1.4.3 — Advanced Visualization**: chart tangga dan batang bertumpuk, warna seri `#RRGGBB`, pilihan legend, ketelitian desimal, titik data, tooltip WITA, konversi satuan tampilan, agregasi min/rata-rata/puncak existing.
- Grafik H/J tetap wajib memakai pasangan jam yang sama dan tidak dapat dijadikan stacked bar; hanya penyajian UI berubah.
- 35 tes backend lulus, import workbook sumber tetap 307 jam / 14.031 nilai. npm/Vite/Docker belum tervalidasi di environment build.
